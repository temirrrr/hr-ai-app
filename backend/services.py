from __future__ import annotations

import csv
import hashlib
import json
import pickle
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from config import settings

DEPARTMENTS_COLUMNS = [
    "id",
    "name",
    "code",
    "parent_id",
    "is_active",
    "created_at",
    "updated_at",
]
POSITIONS_COLUMNS = ["id", "name", "grade", "created_at", "updated_at"]
EMPLOYEES_COLUMNS = [
    "id",
    "employee_code",
    "full_name",
    "email",
    "department_id",
    "position_id",
    "manager_id",
    "hire_date",
    "is_active",
    "created_at",
    "updated_at",
]
PROJECTS_COLUMNS = [
    "project_id",
    "project_code",
    "name",
    "description",
    "department_id",
    "status",
    "start_date",
    "end_date",
    "budget",
    "created_at",
    "updated_at",
]
SYSTEMS_COLUMNS = [
    "system_id",
    "name",
    "system_type",
    "owner_department_id",
    "description",
    "is_active",
    "created_at",
    "updated_at",
]
EMPLOYEE_PROJECTS_COLUMNS = [
    "employee_id",
    "project_id",
    "role",
    "allocation_percent",
    "start_date",
    "end_date",
]
PROJECT_SYSTEMS_COLUMNS = ["project_id", "system_id"]
GOALS_COLUMNS = [
    "goal_id",
    "employee_id",
    "department_id",
    "employee_name_snapshot",
    "position_snapshot",
    "department_name_snapshot",
    "project_id",
    "system_id",
    "goal_text",
    "year",
    "quarter",
    "metric",
    "deadline",
    "weight",
    "status",
    "external_ref",
    "priority",
    "created_at",
    "updated_at",
]
GOAL_EVENTS_COLUMNS = [
    "id",
    "goal_id",
    "event_type",
    "actor_id",
    "old_status",
    "new_status",
    "old_text",
    "new_text",
    "metadata",
    "created_at",
]
GOAL_REVIEWS_COLUMNS = [
    "id",
    "goal_id",
    "reviewer_id",
    "verdict",
    "comment_text",
    "created_at",
]
DOCUMENTS_COLUMNS = [
    "doc_id",
    "doc_type",
    "title",
    "content",
    "valid_from",
    "valid_to",
    "owner_department_id",
    "department_scope",
    "keywords",
    "version",
    "is_active",
    "created_at",
    "updated_at",
]
KPI_CATALOG_COLUMNS = [
    "metric_key",
    "title",
    "unit",
    "description",
    "is_active",
    "created_at",
    "updated_at",
]
KPI_TIMESERIES_COLUMNS = [
    "id",
    "scope_type",
    "department_id",
    "employee_id",
    "project_id",
    "system_id",
    "metric_key",
    "period_date",
    "value_num",
    "metadata",
    "created_at",
]

WEAK_WORDS = {
    "улучшить",
    "повысить",
    "оптимизировать",
    "усилить",
    "развить",
    "проработать",
    "наладить",
}
METRIC_HINTS = {
    "sla",
    "slo",
    "mttr",
    "uptime",
    "kpi",
    "процент",
    "%",
    "количество",
    "доля",
    "срок",
    "метрика",
    "сократить",
    "снизить",
    "увеличить",
    "не менее",
    "не более",
}
TIME_HINTS = {
    "q1",
    "q2",
    "q3",
    "q4",
    "квартал",
    "месяц",
    "неделя",
    "ежемесячно",
    "ежеквартально",
    "до ",
    "к ",
    "срок",
}
ACTIVITY_WORDS = {
    "настроить",
    "внедрить",
    "запустить",
    "подготовить",
    "актуализировать",
    "описать",
    "создать",
    "провести",
    "обновить",
}
IMPACT_WORDS = {
    "эффект",
    "риски",
    "затраты",
    "стоимость",
    "надежность",
    "доступность",
    "качество сервиса",
    "бизнес",
    "производительность",
}
RESULT_WORDS = {
    "достичь",
    "обеспечить",
    "сократить",
    "снизить",
    "увеличить",
    "довести",
    "удержать",
    "повысить",
}


@dataclass(slots=True)
class Period:
    year: int
    quarter: str


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "t", "true", "yes"}


def _to_int(value: Any) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_timestamp(value: Any) -> pd.Timestamp | pd.NaT:
    text = _clean_text(value)
    if not text:
        return pd.NaT
    return pd.to_datetime(text, errors="coerce", utc=True)


def _parse_keywords(raw: str) -> list[str]:
    text = _clean_text(raw).strip("{}")
    if not text:
        return []
    parts = [
        item.strip().strip("'").strip('"')
        for item in text.split(",")
        if item.strip().strip("'").strip('"')
    ]
    return parts


def _parse_department_scope(raw: str) -> list[int]:
    return [int(match) for match in re.findall(r"\d+", _clean_text(raw))]


def _score_to_band(score: float) -> str:
    if score >= 0.78:
        return "strong"
    if score >= 0.55:
        return "watch"
    return "risk"


def _quarter_sort_key(quarter: str) -> int:
    mapping = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    return mapping.get(str(quarter).upper(), 0)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


class LLMClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.llm_api_key)
        self.provider_name = "Rule Engine"
        self.client: OpenAI | None = None
        if self.enabled:
            self.client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout_seconds,
            )
            self.provider_name = settings.llm_model

    def _json_completion(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            return None

    def enhance_evaluation(
        self,
        goal_text: str,
        context: dict[str, Any],
        draft: dict[str, Any],
    ) -> dict[str, Any] | None:
        system_prompt = (
            "Ты senior HR strategist. Преобразуй аналитические сигналы в короткую, "
            "убедительную и деловую оценку цели. Отвечай только JSON."
        )
        user_prompt = json.dumps(
            {
                "goal_text": goal_text,
                "employee_context": context,
                "draft": draft,
                "required_keys": {
                    "specific": "string",
                    "measurable": "string",
                    "achievable": "string",
                    "relevant": "string",
                    "time_bound": "string",
                    "recommendation": ["string"],
                    "improved_version": "string",
                },
            },
            ensure_ascii=False,
        )
        return self._json_completion(system_prompt, user_prompt)

    def generate_proposals(
        self,
        generation_context: dict[str, Any],
        count: int,
    ) -> list[dict[str, Any]] | None:
        system_prompt = (
            "Ты HR/OKR strategist для ИТ-компании. Сгенерируй сильные SMART-цели, "
            "привязанные к источникам, KPI и контексту сотрудника. Верни только JSON."
        )
        user_prompt = json.dumps(
            {
                "generation_context": generation_context,
                "count": count,
                "required_shape": {
                    "items": [
                        {
                            "goal_text": "string",
                            "rationale": "string",
                            "primary_source": "string",
                            "source_quote": "string",
                            "suggested_metric": "string",
                            "suggested_deadline": "string",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )
        payload = self._json_completion(system_prompt, user_prompt)
        if not payload:
            return None
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return None


class HRCommandCenter:
    def __init__(self) -> None:
        self.llm = LLMClient()
        self.data_dir = Path(settings.data_dir)
        self.cache_dir = Path(settings.cache_dir)
        self.cache_hit = False
        signature = self._data_signature()
        if self._restore_cache(signature):
            self.cache_hit = True
            return
        self._load_data()
        self.latest_period = self._detect_latest_period()
        self._build_indexes()
        self.indexed_goals = self._precompute_goal_index()
        self.demo_employee_id = self._pick_demo_employee_id()
        self._persist_cache(signature)

    def _read_rows(self, filename: str) -> list[list[str]]:
        path = self.data_dir / filename
        with path.open("r", encoding="utf-8", newline="") as file:
            return [row for row in csv.reader(file) if any(_clean_text(cell) for cell in row)]

    def _cache_path(self) -> Path:
        return self.cache_dir / "command_center_cache.pkl"

    def _data_signature(self) -> str:
        files = sorted(self.data_dir.glob("*.csv"))
        manifest = [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            for path in files
        ]
        payload = json.dumps(
            {"version": settings.cache_version, "files": manifest},
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _restore_cache(self, signature: str) -> bool:
        path = self._cache_path()
        if not path.exists():
            return False
        try:
            with path.open("rb") as file:
                payload = pickle.load(file)
            if payload.get("signature") != signature:
                return False
            for key, value in payload.get("state", {}).items():
                setattr(self, key, value)
            return True
        except Exception:
            return False

    def _persist_cache(self, signature: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        state = {
            key: getattr(self, key)
            for key in [
                "departments",
                "positions",
                "employees",
                "projects",
                "systems",
                "employee_projects",
                "project_systems",
                "goals",
                "goal_events",
                "goal_reviews",
                "documents",
                "kpi_catalog",
                "kpi_timeseries",
                "latest_period",
                "employee_index",
                "goal_index",
                "goal_events_summary",
                "goal_reviews_latest",
                "latest_kpis",
                "document_vectorizer",
                "document_matrix",
                "goal_vectorizer",
                "goal_matrix",
                "indexed_goals",
                "demo_employee_id",
            ]
        }
        with self._cache_path().open("wb") as file:
            pickle.dump({"signature": signature, "state": state}, file)

    def _frame(self, filename: str, columns: list[str]) -> pd.DataFrame:
        rows = self._read_rows(filename)
        return pd.DataFrame(rows, columns=columns)

    def _repair_documents_rows(self, rows: list[list[str]]) -> list[list[str]]:
        repaired: list[list[str]] = []
        for row in rows:
            prefix = row[:7]
            suffix = row[-4:]
            middle = row[7:-4]
            scope_tokens: list[str] = []
            index = 0
            while index < len(middle):
                scope_tokens.append(middle[index])
                if middle[index].strip().endswith("]}") or middle[index].strip().endswith(']}"'):
                    index += 1
                    break
                index += 1
            keyword_tokens = middle[index:]
            repaired.append(prefix + [",".join(scope_tokens), ",".join(keyword_tokens)] + suffix)
        return repaired

    def _repair_metadata_rows(
        self, rows: list[list[str]], prefix_size: int, suffix_size: int
    ) -> list[list[str]]:
        repaired: list[list[str]] = []
        for row in rows:
            repaired.append(row[:prefix_size] + [",".join(row[prefix_size:-suffix_size])] + row[-suffix_size:])
        return repaired

    def _load_data(self) -> None:
        self.departments = self._frame("departments.csv", DEPARTMENTS_COLUMNS)
        self.positions = self._frame("positions.csv", POSITIONS_COLUMNS)
        self.employees = self._frame("employees.csv", EMPLOYEES_COLUMNS)
        self.projects = self._frame("projects.csv", PROJECTS_COLUMNS)
        self.systems = self._frame("systems.csv", SYSTEMS_COLUMNS)
        self.employee_projects = self._frame("employee_projects.csv", EMPLOYEE_PROJECTS_COLUMNS)
        self.project_systems = self._frame("project_systems.csv", PROJECT_SYSTEMS_COLUMNS)
        self.goals = self._frame("goals.csv", GOALS_COLUMNS)
        self.goal_events = pd.DataFrame(
            self._repair_metadata_rows(self._read_rows("goal_events.csv"), prefix_size=8, suffix_size=1),
            columns=GOAL_EVENTS_COLUMNS,
        )
        self.goal_reviews = self._frame("goal_reviews.csv", GOAL_REVIEWS_COLUMNS)
        self.documents = pd.DataFrame(
            self._repair_documents_rows(self._read_rows("documents.csv")),
            columns=DOCUMENTS_COLUMNS,
        )
        self.kpi_catalog = self._frame("kpi_catalog.csv", KPI_CATALOG_COLUMNS)
        self.kpi_timeseries = pd.DataFrame(
            self._repair_metadata_rows(self._read_rows("kpi_timeseries.csv"), prefix_size=9, suffix_size=1),
            columns=KPI_TIMESERIES_COLUMNS,
        )

        for frame, numeric_columns in [
            (self.departments, ["id", "parent_id"]),
            (self.positions, ["id"]),
            (self.employees, ["id", "department_id", "position_id", "manager_id"]),
            (self.projects, ["department_id"]),
            (self.systems, ["system_id", "owner_department_id"]),
            (self.employee_projects, ["employee_id", "allocation_percent"]),
            (self.project_systems, ["system_id"]),
            (self.goals, ["employee_id", "department_id", "system_id", "year", "priority"]),
            (self.goal_events, ["actor_id"]),
            (self.goal_reviews, ["reviewer_id"]),
            (self.documents, ["owner_department_id"]),
            (self.kpi_timeseries, ["id", "department_id", "employee_id", "system_id"]),
        ]:
            for column in numeric_columns:
                frame[column] = frame[column].map(_to_int)

        for frame, bool_columns in [
            (self.departments, ["is_active"]),
            (self.employees, ["is_active"]),
            (self.systems, ["is_active"]),
            (self.documents, ["is_active"]),
            (self.kpi_catalog, ["is_active"]),
        ]:
            for column in bool_columns:
                frame[column] = frame[column].map(_to_bool)

        for frame, float_columns in [
            (self.projects, ["budget"]),
            (self.goals, ["weight"]),
            (self.kpi_timeseries, ["value_num"]),
        ]:
            for column in float_columns:
                frame[column] = frame[column].map(_to_float)

        for frame, time_columns in [
            (self.employees, ["hire_date", "created_at", "updated_at"]),
            (self.projects, ["start_date", "end_date", "created_at", "updated_at"]),
            (self.systems, ["created_at", "updated_at"]),
            (self.employee_projects, ["start_date", "end_date"]),
            (self.goals, ["deadline", "created_at", "updated_at"]),
            (self.goal_events, ["created_at"]),
            (self.goal_reviews, ["created_at"]),
            (self.documents, ["valid_from", "valid_to", "created_at", "updated_at"]),
            (self.kpi_catalog, ["created_at", "updated_at"]),
            (self.kpi_timeseries, ["period_date", "created_at"]),
        ]:
            for column in time_columns:
                frame[column] = frame[column].map(_to_timestamp)

        self.documents["department_scope_ids"] = self.documents["department_scope"].map(_parse_department_scope)
        self.documents["keyword_list"] = self.documents["keywords"].map(_parse_keywords)
        self.goals["goal_text"] = self.goals["goal_text"].map(_clean_text)
        self.goals["metric"] = self.goals["metric"].map(_clean_text)
        self.documents["title"] = self.documents["title"].map(_clean_text)
        self.documents["content"] = self.documents["content"].map(_clean_text)

    def _build_indexes(self) -> None:
        dept_lookup = self.departments.rename(
            columns={"id": "department_id", "name": "department_name", "code": "department_code"}
        )[["department_id", "department_name", "department_code"]]
        position_lookup = self.positions.rename(
            columns={"id": "position_id", "name": "position_name", "grade": "position_grade"}
        )[["position_id", "position_name", "position_grade"]]

        self.employee_index = (
            self.employees.merge(dept_lookup, on="department_id", how="left")
            .merge(position_lookup, on="position_id", how="left")
            .copy()
        )
        manager_lookup = self.employee_index[["id", "full_name"]].rename(
            columns={"id": "manager_id", "full_name": "manager_name"}
        )
        self.employee_index = self.employee_index.merge(manager_lookup, on="manager_id", how="left")

        project_lookup = self.projects[["project_id", "name", "status"]].rename(
            columns={"name": "project_name", "status": "project_status"}
        )
        system_lookup = self.systems[["system_id", "name", "system_type"]].rename(
            columns={"name": "system_name"}
        )
        self.goal_index = (
            self.goals.merge(project_lookup, on="project_id", how="left")
            .merge(system_lookup, on="system_id", how="left")
            .merge(
                self.employee_index[
                    ["id", "full_name", "department_name", "position_name", "manager_id", "manager_name"]
                ].rename(columns={"id": "employee_id"}),
                on="employee_id",
                how="left",
            )
            .copy()
        )

        self.documents["is_current"] = self.documents["valid_to"].isna() | (
            self.documents["valid_to"] >= pd.Timestamp.now(tz=UTC)
        )
        self.documents["search_text"] = self.documents.apply(
            lambda row: _clean_text(
                " ".join(
                    [
                        row["title"],
                        row["content"],
                        " ".join(row["keyword_list"]),
                        self._department_name_from_id(row["owner_department_id"]),
                    ]
                )
            ),
            axis=1,
        )
        self.goals["search_text"] = self.goals["goal_text"].map(_clean_text)

        self.goal_events_summary = (
            self.goal_events.groupby("goal_id")["event_type"].agg(lambda values: list(values)).to_dict()
        )
        self.goal_reviews_latest = (
            self.goal_reviews.sort_values("created_at")
            .groupby("goal_id")
            .tail(1)
            .set_index("goal_id")["comment_text"]
            .to_dict()
        )

        self.latest_kpis = (
            self.kpi_timeseries.sort_values("period_date")
            .groupby(["scope_type", "department_id", "metric_key"])
            .tail(1)
            .merge(self.kpi_catalog[["metric_key", "title", "unit"]], on="metric_key", how="left")
            .copy()
        )

        self.document_vectorizer, self.document_matrix = self._build_vectorizer(
            self.documents["search_text"].fillna("").tolist(),
            max_features=3500,
        )
        self.goal_vectorizer, self.goal_matrix = self._build_vectorizer(
            self.goals["search_text"].fillna("").tolist(),
            max_features=5000,
        )

    def _detect_latest_period(self) -> Period:
        ordered = self.goals.assign(
            quarter_order=self.goals["quarter"].map(_quarter_sort_key),
        ).sort_values(["year", "quarter_order"], ascending=[False, False])
        latest_row = ordered.iloc[0]
        return Period(year=int(latest_row["year"]), quarter=str(latest_row["quarter"]))

    def _build_vectorizer(self, texts: list[str], max_features: int) -> tuple[TfidfVectorizer, Any]:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=max_features)
        matrix = vectorizer.fit_transform(texts)
        return vectorizer, matrix

    def _precompute_goal_index(self) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        for row in self.goal_index.itertuples(index=False):
            quick = self._quick_goal_diagnostics(
                goal_text=row.goal_text,
                metric=row.metric,
                deadline=row.deadline,
                context_text=" ".join(
                    [
                        _clean_text(row.department_name),
                        _clean_text(row.position_name),
                        _clean_text(row.project_name),
                        _clean_text(row.system_name),
                    ]
                ),
            )
            records.append(
                {
                    "goal_id": row.goal_id,
                    "employee_id": row.employee_id,
                    "year": row.year,
                    "quarter": row.quarter,
                    "department_name": _clean_text(row.department_name or row.department_name_snapshot),
                    "position_name": _clean_text(row.position_name or row.position_snapshot),
                    "status": row.status,
                    "goal_type": quick["goal_type"],
                    "smart_score": quick["smart_score"],
                    "alignment_score": quick["alignment_score"],
                    "missing_metric": quick["missing_metric"],
                    "missing_deadline": quick["missing_deadline"],
                    "vague_goal": quick["vague_goal"],
                    "goal_text": row.goal_text,
                }
            )
        return pd.DataFrame(records)

    def _pick_demo_employee_id(self) -> int:
        candidate_scores: list[tuple[int, float]] = []
        for row in self.employee_index.itertuples(index=False):
            goals = self.goal_index[self.goal_index["employee_id"] == row.id]
            projects = self.employee_projects[self.employee_projects["employee_id"] == row.id]
            score = (
                min(len(goals), 6) * 1.7
                + min(len(projects), 3) * 1.5
                + (1.0 if row.manager_id else 0.0)
                + (1.0 if goals["status"].isin(["approved", "in_progress", "done"]).any() else 0.0)
            )
            candidate_scores.append((int(row.id), score))
        candidate_scores.sort(key=lambda item: item[1], reverse=True)
        return candidate_scores[0][0] if candidate_scores else 1

    def _department_name_from_id(self, department_id: int | None) -> str:
        if department_id is None:
            return ""
        match = self.departments[self.departments["id"] == department_id]
        if match.empty:
            return ""
        return _clean_text(match.iloc[0]["name"])

    def _goal_set_for_employee(self, employee_id: int, period: Period | None = None) -> pd.DataFrame:
        scope = self.goal_index[self.goal_index["employee_id"] == employee_id].copy()
        if scope.empty:
            return scope
        active_period = period or self._employee_latest_period(employee_id)
        return scope[
            (scope["year"] == active_period.year)
            & (scope["quarter"] == active_period.quarter)
        ].copy()

    def _employee_latest_period(self, employee_id: int) -> Period:
        goals = self.goal_index[self.goal_index["employee_id"] == employee_id].copy()
        if goals.empty:
            return self.latest_period
        goals["quarter_order"] = goals["quarter"].map(_quarter_sort_key)
        row = goals.sort_values(["year", "quarter_order"], ascending=[False, False]).iloc[0]
        return Period(year=int(row["year"]), quarter=str(row["quarter"]))

    def _quick_goal_diagnostics(
        self,
        goal_text: str,
        metric: str | None = None,
        deadline: pd.Timestamp | None = None,
        context_text: str = "",
    ) -> dict[str, Any]:
        text = _clean_text(goal_text)
        lower = text.lower()
        metric_text = _clean_text(metric).lower()
        combined = f"{lower} {metric_text} {context_text.lower()}".strip()

        has_number = bool(re.search(r"\d", combined))
        has_metric = has_number or any(token in combined for token in METRIC_HINTS)
        has_time = pd.notna(deadline) or any(token in combined for token in TIME_HINTS) or bool(
            re.search(r"\b20\d{2}\b", combined)
        )
        vague = any(lower.startswith(word) for word in WEAK_WORDS) and not has_metric
        specific_raw = 0.45 + (0.15 if len(text.split()) >= 8 else 0.0) + (0.15 if context_text else 0.0)
        if vague:
            specific_raw -= 0.18
        measurable_raw = 0.25 + (0.55 if has_metric else 0.0)
        time_raw = 0.2 + (0.7 if has_time else 0.0)
        alignment_raw = 0.35 + (0.35 if context_text else 0.0) + (0.15 if any(item in lower for item in IMPACT_WORDS) else 0.0)
        achievable_raw = 0.5 + (0.1 if len(text.split()) <= 24 else -0.08) + (0.12 if has_metric else -0.04)

        smart_score = round(
            min(1.0, max(0.0, (specific_raw + measurable_raw + time_raw + alignment_raw + achievable_raw) / 5)),
            3,
        )
        goal_type = self._classify_goal_type(text)
        return {
            "smart_score": smart_score,
            "specific_score": round(min(1.0, max(0.0, specific_raw)), 3),
            "measurable_score": round(min(1.0, max(0.0, measurable_raw)), 3),
            "time_score": round(min(1.0, max(0.0, time_raw)), 3),
            "alignment_score": round(min(1.0, max(0.0, alignment_raw)), 3),
            "achievable_score": round(min(1.0, max(0.0, achievable_raw)), 3),
            "goal_type": goal_type,
            "missing_metric": not has_metric,
            "missing_deadline": not has_time,
            "vague_goal": vague,
        }

    def _retrieve_documents(
        self,
        employee: pd.Series,
        focus_priority: str | None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        query_parts = [
            employee.get("department_name", ""),
            employee.get("position_name", ""),
            focus_priority or "",
            employee.get("full_name", ""),
        ]
        employee_projects = self._project_cards(int(employee["id"]))
        query_parts.extend(project["project_name"] for project in employee_projects[:2])
        query = _clean_text(" ".join(query_parts))
        query_vector = self.document_vectorizer.transform([query])
        similarities = linear_kernel(query_vector, self.document_matrix).flatten()

        docs = self.documents.copy()
        docs["similarity"] = similarities
        dept_id = employee.get("department_id")
        docs["scope_match"] = docs["department_scope_ids"].map(
            lambda ids: 1.0 if not ids or dept_id in ids else 0.0
        )
        docs["priority"] = docs["similarity"] + docs["scope_match"] * 0.18 + docs["is_current"].astype(float) * 0.08
        docs = docs.sort_values("priority", ascending=False).head(limit)

        results: list[dict[str, Any]] = []
        for row in docs.itertuples(index=False):
            quote = self._pick_source_quote(row.content, focus_priority or employee.get("position_name", ""))
            results.append(
                {
                    "doc_id": row.doc_id,
                    "title": row.title,
                    "doc_type": row.doc_type,
                    "source_quote": quote,
                    "keywords": row.keyword_list[:6],
                    "similarity": round(float(row.priority), 3),
                    "department_fit": bool(not row.department_scope_ids or dept_id in row.department_scope_ids),
                }
            )
        return results

    def _pick_source_quote(self, content: str, query_hint: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", content)
        hint_tokens = {token for token in _clean_text(query_hint).lower().split() if len(token) > 3}
        if hint_tokens:
            ranked = sorted(
                sentences,
                key=lambda sentence: sum(token in sentence.lower() for token in hint_tokens),
                reverse=True,
            )
        else:
            ranked = sentences
        quote = _clean_text(ranked[0] if ranked else content)
        return quote[:260].rstrip() + ("..." if len(quote) > 260 else "")

    def _project_cards(self, employee_id: int) -> list[dict[str, Any]]:
        links = self.employee_projects[self.employee_projects["employee_id"] == employee_id].copy()
        if links.empty:
            return []
        merged = links.merge(
            self.projects[["project_id", "project_code", "name", "status", "description"]],
            on="project_id",
            how="left",
        )
        cards: list[dict[str, Any]] = []
        for row in merged.itertuples(index=False):
            cards.append(
                {
                    "project_id": row.project_id,
                    "project_code": row.project_code,
                    "project_name": row.name,
                    "role": _clean_text(row.role),
                    "allocation_percent": _to_int(row.allocation_percent),
                    "status": _clean_text(row.status),
                    "description": _clean_text(row.description),
                }
            )
        return cards

    def _manager_goals(self, employee: pd.Series, period: Period) -> list[dict[str, Any]]:
        manager_id = employee.get("manager_id")
        if not manager_id:
            return []
        goals = self.goal_index[
            (self.goal_index["employee_id"] == manager_id)
            & (self.goal_index["year"] == period.year)
            & (self.goal_index["quarter"] == period.quarter)
        ].copy()
        goals = goals.sort_values("weight", ascending=False).head(3)
        return [
            {
                "goal_id": row.goal_id,
                "goal_text": row.goal_text,
                "status": row.status,
                "weight": row.weight,
            }
            for row in goals.itertuples(index=False)
        ]

    def _latest_kpi_highlights(self, employee: pd.Series) -> list[dict[str, Any]]:
        dept_id = employee.get("department_id")
        scoped = self.latest_kpis[
            ((self.latest_kpis["scope_type"] == "department") & (self.latest_kpis["department_id"] == dept_id))
            | (self.latest_kpis["scope_type"] == "company")
        ].copy()
        scoped = scoped.sort_values("period_date", ascending=False).drop_duplicates("metric_key")
        results: list[dict[str, Any]] = []
        for row in scoped.head(5).itertuples(index=False):
            results.append(
                {
                    "metric_key": row.metric_key,
                    "title": row.title,
                    "value": round(float(row.value_num or 0.0), 2),
                    "unit": row.unit,
                    "scope_type": row.scope_type,
                }
            )
        return results

    def _classify_goal_type(self, goal_text: str) -> str:
        lower = goal_text.lower()
        if any(token in lower for token in IMPACT_WORDS):
            return "impact-based"
        if any(token in lower for token in RESULT_WORDS) and bool(re.search(r"\d|%|срок|sla|uptime|mttr", lower)):
            return "output-based"
        if any(token in lower for token in ACTIVITY_WORDS):
            return "activity-based"
        return "output-based"

    def _find_similar_goals(
        self,
        goal_text: str,
        employee: pd.Series | None = None,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        query_vector = self.goal_vectorizer.transform([_clean_text(goal_text)])
        similarities = linear_kernel(query_vector, self.goal_matrix).flatten()
        candidates = self.goal_index.copy()
        candidates["similarity"] = similarities
        if employee is not None:
            dept_name = _clean_text(employee.get("department_name"))
            candidates = candidates[
                (candidates["department_name"].fillna("") == dept_name)
                | (candidates["position_name"].fillna("") == _clean_text(employee.get("position_name")))
            ]
        candidates = candidates.sort_values("similarity", ascending=False)
        results: list[dict[str, Any]] = []
        for row in candidates.head(limit).itertuples(index=False):
            results.append(
                {
                    "goal_id": row.goal_id,
                    "goal_text": row.goal_text,
                    "employee_name": row.full_name,
                    "status": row.status,
                    "similarity": round(float(row.similarity), 3),
                }
            )
        return results

    def _alignment_level(self, score: float, manager_overlap: float) -> str:
        if score >= 0.72 and manager_overlap >= 0.1:
            return "strategic"
        if score >= 0.55:
            return "functional"
        return "operational"

    def _similarity_to_texts(self, goal_text: str, texts: list[str]) -> float:
        if not texts:
            return 0.0
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1200)
        matrix = vectorizer.fit_transform([_clean_text(goal_text)] + [_clean_text(text) for text in texts])
        similarities = linear_kernel(matrix[0:1], matrix[1:]).flatten()
        return float(similarities.max()) if len(similarities) else 0.0

    def _evaluate_goal_core(
        self,
        goal_text: str,
        employee: pd.Series | None,
        focus_priority: str | None = None,
        metric: str | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        employee_context_text = ""
        docs: list[dict[str, Any]] = []
        manager_goals: list[dict[str, Any]] = []
        kpis: list[dict[str, Any]] = []
        if employee is not None:
            docs = self._retrieve_documents(employee, focus_priority, limit=4)
            period = self._employee_latest_period(int(employee["id"]))
            manager_goals = self._manager_goals(employee, period)
            kpis = self._latest_kpi_highlights(employee)
            employee_context_text = " ".join(
                [
                    _clean_text(employee.get("department_name")),
                    _clean_text(employee.get("position_name")),
                    " ".join(item["title"] for item in docs),
                    " ".join(goal["goal_text"] for goal in manager_goals),
                    " ".join(kpi["title"] for kpi in kpis),
                ]
            )

        quick = self._quick_goal_diagnostics(goal_text, metric=metric, deadline=_to_timestamp(deadline), context_text=employee_context_text)
        similar_goals = self._find_similar_goals(goal_text, employee=employee)
        similar_score = similar_goals[0]["similarity"] if similar_goals else 0.0
        manager_overlap = self._similarity_to_texts(goal_text, [goal["goal_text"] for goal in manager_goals])
        doc_overlap = self._similarity_to_texts(goal_text, [doc["title"] + " " + doc["source_quote"] for doc in docs])
        kpi_overlap = self._similarity_to_texts(goal_text, [kpi["title"] for kpi in kpis])
        alignment_score = round(
            min(
                1.0,
                max(
                    quick["alignment_score"],
                    0.38 + doc_overlap * 0.36 + manager_overlap * 0.22 + kpi_overlap * 0.2,
                ),
            ),
            3,
        )
        achievable_adjusted = min(
            1.0,
            max(
                0.0,
                quick["achievable_score"]
                + (0.08 if similar_score >= 0.62 else 0.0)
                - (0.12 if len(_clean_text(goal_text).split(";")) > 2 else 0.0),
            ),
        )
        overall_score = round(
            (
                quick["specific_score"]
                + quick["measurable_score"]
                + achievable_adjusted
                + alignment_score
                + quick["time_score"]
            )
            / 5,
            3,
        )
        goal_type = quick["goal_type"]
        duplicate_risk = "high" if similar_score >= 0.82 else "medium" if similar_score >= 0.68 else "low"
        alignment_level = self._alignment_level(alignment_score, manager_overlap)

        weaknesses = []
        if quick["missing_metric"]:
            weaknesses.append("Нет чёткой метрики результата.")
        if quick["missing_deadline"]:
            weaknesses.append("Нет понятного срока выполнения.")
        if quick["vague_goal"]:
            weaknesses.append("Формулировка стартует с расплывчатого глагола без результата.")
        if goal_type == "activity-based":
            weaknesses.append("Цель выглядит как список действий, а не как измеримый результат.")
        if duplicate_risk != "low":
            weaknesses.append("Формулировка близка к уже существующим целям и может дублировать набор.")
        if alignment_level == "operational":
            weaknesses.append("Связка с KPI, ВНД или целями руководителя слабая.")

        recommendations = self._build_recommendations(
            goal_text=goal_text,
            goal_type=goal_type,
            alignment_level=alignment_level,
            missing_metric=quick["missing_metric"],
            missing_deadline=quick["missing_deadline"],
            duplicate_risk=duplicate_risk,
            docs=docs,
            kpis=kpis,
        )
        improved_version = self._rewrite_goal(
            goal_text=goal_text,
            metric_hint=metric or (kpis[0]["title"] if kpis else ""),
            deadline_hint=deadline or self._default_deadline_text(employee),
            goal_type=goal_type,
        )

        return {
            "score": overall_score,
            "specific_score": quick["specific_score"],
            "measurable_score": quick["measurable_score"],
            "achievable_score": round(achievable_adjusted, 3),
            "relevant_score": alignment_score,
            "time_score": quick["time_score"],
            "goal_type": goal_type,
            "alignment_score": alignment_score,
            "alignment_level": alignment_level,
            "duplicate_risk": duplicate_risk,
            "similar_goals": similar_goals,
            "evidence": docs,
            "manager_goals": manager_goals,
            "kpis": kpis,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "improved_version": improved_version,
        }

    def _default_deadline_text(self, employee: pd.Series | None) -> str:
        if employee is None:
            return f"до конца {self.latest_period.quarter} {self.latest_period.year}"
        period = self._employee_latest_period(int(employee["id"]))
        return f"до конца {period.quarter} {period.year}"

    def _rewrite_goal(
        self,
        goal_text: str,
        metric_hint: str,
        deadline_hint: str,
        goal_type: str,
    ) -> str:
        text = _clean_text(goal_text)
        if goal_type == "activity-based":
            lead = "Обеспечить измеримый результат по инициативе"
        else:
            lead = text.split(".")[0]
        if metric_hint and metric_hint.lower() not in text.lower():
            metric_part = f", с подтверждением по метрике «{metric_hint}»"
        else:
            metric_part = ", с измеримым целевым показателем"
        deadline_part = f" {deadline_hint}" if deadline_hint else ""
        rewritten = f"{lead}{metric_part} и закрепить результат{deadline_part}."
        return _clean_text(rewritten)

    def _build_recommendations(
        self,
        goal_text: str,
        goal_type: str,
        alignment_level: str,
        missing_metric: bool,
        missing_deadline: bool,
        duplicate_risk: str,
        docs: list[dict[str, Any]],
        kpis: list[dict[str, Any]],
    ) -> list[str]:
        recommendations: list[str] = []
        if goal_type == "activity-based":
            recommendations.append("Переведи цель из активности в результат: что именно должно улучшиться и как это проверить.")
        if missing_metric:
            metric_title = kpis[0]["title"] if kpis else "SLA / скорость / качество"
            recommendations.append(f"Добавь одну основную метрику достижения, например через показатель «{metric_title}».")
        if missing_deadline:
            recommendations.append("Зафиксируй срок: квартал, дата или регулярность контроля результата.")
        if alignment_level != "strategic" and docs:
            recommendations.append(f"Привяжи цель к документу «{docs[0]['title']}» и явно покажи связь с нормативным требованием.")
        if duplicate_risk != "low":
            recommendations.append("Разведи цель с соседними задачами: уточни объект, эффект и уникальную метрику.")
        if not recommendations:
            recommendations.append("Цель уже выглядит сильно. Усиль её краткой метрикой эффекта и источником стратегической связки.")
        return recommendations[:4]

    def _fallback_evaluation_text(self, core: dict[str, Any]) -> dict[str, str]:
        return {
            "specific": (
                "Цель звучит предметно и привязана к реальному объекту работы."
                if core["specific_score"] >= 0.7
                else "Формулировка пока слишком общая. Нужен более чёткий объект воздействия и ожидаемый результат."
            ),
            "measurable": (
                "Измеримость читается хорошо: есть ориентир для проверки результата."
                if core["measurable_score"] >= 0.7
                else "Измеримость слабая: не хватает одной явной метрики, по которой можно принять цель."
            ),
            "achievable": (
                "Для роли и контекста цель выглядит реалистично, особенно с учётом похожих целей в истории."
                if core["achievable_score"] >= 0.7
                else "Достижимость вызывает вопросы: цель либо слишком расплывчата, либо перегружена несколькими результатами сразу."
            ),
            "relevant": (
                "Связка с ролью, документами и приоритетами заметна."
                if core["alignment_score"] >= 0.68
                else "Релевантность пока неочевидна. Нужно явнее связать цель с KPI, ВНД или целями руководителя."
            ),
            "time_bound": (
                "Срок или период контроля понятен."
                if core["time_score"] >= 0.7
                else "Во времени цель пока не зафиксирована. Нужно добавить дату, квартал или регулярность."
            ),
        }

    def evaluate_goal(
        self,
        goal_text: str,
        employee_id: int | None = None,
        focus_priority: str | None = None,
        metric: str | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        employee = None
        if employee_id is not None:
            match = self.employee_index[self.employee_index["id"] == employee_id]
            if not match.empty:
                employee = match.iloc[0]
        core = self._evaluate_goal_core(goal_text, employee, focus_priority=focus_priority, metric=metric, deadline=deadline)
        text_sections = self._fallback_evaluation_text(core)
        llm_enhanced = self.llm.enhance_evaluation(
            goal_text=goal_text,
            context=self._employee_brief(employee) if employee is not None else {},
            draft={**core, **text_sections},
        )
        if llm_enhanced:
            text_sections.update(
                {
                    key: _clean_text(llm_enhanced.get(key)) or value
                    for key, value in text_sections.items()
                }
            )
            if llm_enhanced.get("recommendation"):
                core["recommendations"] = [
                    _clean_text(item)
                    for item in llm_enhanced["recommendation"]
                    if _clean_text(item)
                ][:4]
            if llm_enhanced.get("improved_version"):
                core["improved_version"] = _clean_text(llm_enhanced["improved_version"])

        set_health = self._goal_set_health(employee_id)
        return {
            "evaluation": {
                "specific": text_sections["specific"],
                "measurable": text_sections["measurable"],
                "achievable": text_sections["achievable"],
                "relevant": text_sections["relevant"],
                "time_bound": text_sections["time_bound"],
                "score": core["score"],
                "recommendation": core["recommendations"],
                "improved_version": core["improved_version"],
            },
            "insights": {
                "alignment_score": core["alignment_score"],
                "alignment_level": core["alignment_level"],
                "goal_type": core["goal_type"],
                "duplicate_risk": core["duplicate_risk"],
                "weaknesses": core["weaknesses"],
                "similar_goals": core["similar_goals"],
                "evidence": core["evidence"],
                "set_health": set_health,
                "llm_mode": self.llm.provider_name,
            },
        }

    def _goal_set_health(self, employee_id: int | None) -> dict[str, Any]:
        if employee_id is None:
            return {"goal_count": 0, "weight_total": 0.0, "issues": []}
        period = self._employee_latest_period(employee_id)
        goals = self._goal_set_for_employee(employee_id, period)
        issues: list[str] = []
        goal_count = len(goals)
        weight_total = round(float(goals["weight"].fillna(0).sum()), 2)
        if goal_count < 3:
            issues.append("У сотрудника меньше 3 целей в наборе.")
        if goal_count > 5:
            issues.append("У сотрудника больше 5 целей, набор перегружен.")
        if abs(weight_total - 100.0) > 10:
            issues.append("Суммарный вес целей заметно отличается от 100%.")
        duplicates = 0
        texts = goals["goal_text"].tolist()
        if len(texts) >= 2:
            duplicates = sum(
                1
                for index, text in enumerate(texts)
                if self._similarity_to_texts(text, texts[:index] + texts[index + 1 :]) >= 0.75
            )
        if duplicates:
            issues.append("В наборе есть потенциально дублирующиеся цели.")
        return {
            "goal_count": goal_count,
            "weight_total": weight_total,
            "period": {"year": period.year, "quarter": period.quarter},
            "issues": issues,
            "status": "healthy" if not issues else "watch",
        }

    def _employee_brief(self, employee: pd.Series | None) -> dict[str, Any]:
        if employee is None:
            return {}
        return {
            "employee_id": int(employee["id"]),
            "full_name": employee["full_name"],
            "department": employee["department_name"],
            "position": employee["position_name"],
            "manager_name": employee["manager_name"],
        }

    def _fallback_generated_goals(
        self,
        employee: pd.Series,
        focus_priority: str | None,
        count: int,
    ) -> list[dict[str, Any]]:
        docs = self._retrieve_documents(employee, focus_priority, limit=max(count, 4))
        kpis = self._latest_kpi_highlights(employee)
        manager_goals = self._manager_goals(employee, self._employee_latest_period(int(employee["id"])))
        projects = self._project_cards(int(employee["id"]))
        ideas: list[dict[str, Any]] = []

        for doc in docs:
            metric_hint = kpis[0]["title"] if kpis else "SLA compliance"
            project_part = f" в рамках проекта «{projects[0]['project_name']}»" if projects else ""
            focus_part = f" с фокусом на {focus_priority}" if focus_priority else ""
            goal_text = (
                f"Обеспечить улучшение по направлению «{doc['title']}»{project_part}{focus_part}, "
                f"зафиксировав результат по метрике «{metric_hint}» до конца {self._employee_latest_period(int(employee['id'])).quarter} {self._employee_latest_period(int(employee['id'])).year}."
            )
            ideas.append(
                {
                    "goal_text": goal_text,
                    "rationale": "Цель привязана к релевантному ВНД и усиливает управляемость результата.",
                    "primary_source": doc["title"],
                    "source_quote": doc["source_quote"],
                    "suggested_metric": metric_hint,
                    "suggested_deadline": self._default_deadline_text(employee),
                }
            )

        for goal in manager_goals:
            ideas.append(
                {
                    "goal_text": (
                        f"Скаскадировать цель руководителя «{goal['goal_text']}» в персональный результат, "
                        f"сформулировав собственную метрику эффекта до {self._default_deadline_text(employee)}."
                    ),
                    "rationale": "Цель усиливает вертикальную связку между сотрудником и руководителем.",
                    "primary_source": "Цель руководителя",
                    "source_quote": goal["goal_text"],
                    "suggested_metric": "персональный KPI по зоне ответственности",
                    "suggested_deadline": self._default_deadline_text(employee),
                }
            )

        deduped: list[dict[str, Any]] = []
        seen: list[str] = []
        for item in ideas:
            if self._similarity_to_texts(item["goal_text"], seen) < 0.72:
                deduped.append(item)
                seen.append(item["goal_text"])
            if len(deduped) == count:
                break
        return deduped[:count]

    def generate_goals(
        self,
        employee_id: int,
        focus_priority: str | None = None,
        count: int = 4,
    ) -> dict[str, Any]:
        match = self.employee_index[self.employee_index["id"] == employee_id]
        if match.empty:
            raise KeyError("Employee not found")
        employee = match.iloc[0]
        docs = self._retrieve_documents(employee, focus_priority, limit=5)
        period = self._employee_latest_period(employee_id)
        context = {
            "employee": self._employee_brief(employee),
            "focus_priority": focus_priority,
            "period": {"year": period.year, "quarter": period.quarter},
            "projects": self._project_cards(employee_id),
            "manager_goals": self._manager_goals(employee, period),
            "kpis": self._latest_kpi_highlights(employee),
            "documents": docs,
        }
        proposals = self.llm.generate_proposals(context, count=count) or self._fallback_generated_goals(
            employee, focus_priority, count
        )

        ranked: list[dict[str, Any]] = []
        for item in proposals:
            evaluation = self._evaluate_goal_core(
                goal_text=_clean_text(item.get("goal_text")),
                employee=employee,
                focus_priority=focus_priority,
                metric=_clean_text(item.get("suggested_metric")),
                deadline=_clean_text(item.get("suggested_deadline")),
            )
            ranked.append(
                {
                    "goal_text": _clean_text(item.get("goal_text")),
                    "source_document": _clean_text(item.get("primary_source")) or (docs[0]["title"] if docs else "AI synthesis"),
                    "source_quote": _clean_text(item.get("source_quote")) or (docs[0]["source_quote"] if docs else ""),
                    "smart_score": evaluation["score"],
                    "alignment_score": evaluation["alignment_score"],
                    "alignment_level": evaluation["alignment_level"],
                    "goal_type": evaluation["goal_type"],
                    "context_reasoning": _clean_text(item.get("rationale"))
                    or "Предложение учитывает роль сотрудника, KPI и релевантные ВНД.",
                    "recommendations": evaluation["recommendations"],
                    "improved_version": evaluation["improved_version"],
                }
            )

        ranked.sort(key=lambda item: (item["smart_score"], item["alignment_score"]), reverse=True)
        return {
            "employee": self._employee_brief(employee),
            "period": {"year": period.year, "quarter": period.quarter},
            "proposals": ranked[:count],
            "sources": docs,
            "llm_mode": self.llm.provider_name,
        }

    def search_employees(self, query: str = "", limit: int = 12) -> list[dict[str, Any]]:
        scope = self.employee_index.copy()
        if query:
            lowered = query.lower()
            scope = scope[
                scope["full_name"].str.lower().str.contains(lowered, na=False)
                | scope["employee_code"].str.lower().str.contains(lowered, na=False)
                | scope["department_name"].str.lower().str.contains(lowered, na=False)
                | scope["position_name"].str.lower().str.contains(lowered, na=False)
            ]
        scope = scope.sort_values("full_name").head(limit)
        return [
            {
                "id": int(row.id),
                "full_name": row.full_name,
                "employee_code": row.employee_code,
                "department_name": row.department_name,
                "position_name": row.position_name,
            }
            for row in scope.itertuples(index=False)
        ]

    def get_employee_workspace(self, employee_id: int) -> dict[str, Any]:
        match = self.employee_index[self.employee_index["id"] == employee_id]
        if match.empty:
            raise KeyError("Employee not found")
        employee = match.iloc[0]
        period = self._employee_latest_period(employee_id)
        current_goals = self._goal_set_for_employee(employee_id, period)
        goal_cards: list[dict[str, Any]] = []
        issue_counter: Counter[str] = Counter()
        scores: list[float] = []
        for row in current_goals.itertuples(index=False):
            evaluation = self._evaluate_goal_core(
                goal_text=row.goal_text,
                employee=employee,
                metric=row.metric,
                deadline=row.deadline.isoformat() if pd.notna(row.deadline) else None,
            )
            scores.append(evaluation["score"])
            for weakness in evaluation["weaknesses"]:
                issue_counter[weakness] += 1
            goal_cards.append(
                {
                    "goal_id": row.goal_id,
                    "goal_text": row.goal_text,
                    "status": row.status,
                    "weight": _to_float(row.weight),
                    "smart_score": evaluation["score"],
                    "alignment_level": evaluation["alignment_level"],
                    "goal_type": evaluation["goal_type"],
                    "review_comment": self.goal_reviews_latest.get(row.goal_id, ""),
                }
            )

        history = self.goal_index[self.goal_index["employee_id"] == employee_id]
        completed_share = round(
            float((history["status"] == "done").mean()) if not history.empty else 0.0,
            3,
        )
        approved_share = round(
            float(history["status"].isin(["approved", "in_progress", "done"]).mean()) if not history.empty else 0.0,
            3,
        )
        top_issues = [{"label": key, "count": value} for key, value in issue_counter.most_common(4)]

        return {
            "employee": {
                **self._employee_brief(employee),
                "email": employee["email"],
                "tenure_years": round(
                    (
                        (pd.Timestamp.now(tz=UTC) - employee["hire_date"]).days / 365.25
                        if pd.notna(employee["hire_date"])
                        else 0.0
                    ),
                    1,
                ),
            },
            "period": {"year": period.year, "quarter": period.quarter},
            "health": {
                **self._goal_set_health(employee_id),
                "avg_smart_score": _mean(scores),
                "approved_share": approved_share,
                "completed_share": completed_share,
            },
            "projects": self._project_cards(employee_id),
            "manager_goals": self._manager_goals(employee, period),
            "documents": self._retrieve_documents(employee, focus_priority=None, limit=4),
            "kpis": self._latest_kpi_highlights(employee),
            "current_goals": goal_cards,
            "top_issues": top_issues,
        }

    def get_dashboard(self) -> dict[str, Any]:
        frame = self.indexed_goals[
            (self.indexed_goals["year"] == self.latest_period.year)
            & (self.indexed_goals["quarter"] == self.latest_period.quarter)
        ].copy()
        department_stats = (
            frame.groupby("department_name")
            .agg(
                goals=("goal_id", "count"),
                avg_smart_score=("smart_score", "mean"),
                avg_alignment=("alignment_score", "mean"),
                missing_metric=("missing_metric", "sum"),
                missing_deadline=("missing_deadline", "sum"),
                activity_goals=("goal_type", lambda values: sum(value == "activity-based" for value in values)),
            )
            .reset_index()
            .sort_values("avg_smart_score", ascending=False)
        )

        department_rankings = [
            {
                "department_name": row.department_name,
                "goals": int(row.goals),
                "avg_smart_score": round(float(row.avg_smart_score), 3),
                "avg_alignment": round(float(row.avg_alignment), 3),
                "risk_band": _score_to_band(float(row.avg_smart_score)),
                "headline": (
                    "Сильная зрелость целей"
                    if row.avg_smart_score >= 0.72
                    else "Есть потенциал на улучшение"
                ),
            }
            for row in department_stats.head(8).itertuples(index=False)
        ]

        issue_counts = Counter()
        issue_counts["Без метрики"] = int(frame["missing_metric"].sum())
        issue_counts["Без срока"] = int(frame["missing_deadline"].sum())
        issue_counts["Activity-based"] = int((frame["goal_type"] == "activity-based").sum())
        issue_counts["Низкая стратегическая связка"] = int((frame["alignment_score"] < 0.55).sum())
        risk_clusters = [
            {"label": label, "count": count}
            for label, count in issue_counts.most_common(4)
        ]

        spotlight = frame.sort_values(["smart_score", "alignment_score"]).head(5)
        spotlight_goals = [
            {
                "goal_id": row.goal_id,
                "goal_text": row.goal_text,
                "department_name": row.department_name,
                "smart_score": round(float(row.smart_score), 3),
                "alignment_score": round(float(row.alignment_score), 3),
            }
            for row in spotlight.itertuples(index=False)
        ]

        kpi_watch = [
            {
                "title": row.title,
                "value": round(float(row.value_num or 0.0), 2),
                "unit": row.unit,
                "scope_type": row.scope_type,
            }
            for row in self.latest_kpis.sort_values("period_date", ascending=False)
            .drop_duplicates("metric_key")
            .head(6)
            .itertuples(index=False)
        ]

        summary = {
            "employees": int(len(self.employee_index)),
            "goals": int(len(self.goal_index)),
            "documents": int(len(self.documents)),
            "avg_smart_score": round(float(frame["smart_score"].mean()), 3),
            "alignment_coverage": round(float((frame["alignment_score"] >= 0.6).mean()), 3),
            "activity_goal_share": round(float((frame["goal_type"] == "activity-based").mean()), 3),
        }
        return {
            "summary": summary,
            "period": {"year": self.latest_period.year, "quarter": self.latest_period.quarter},
            "department_rankings": department_rankings,
            "risk_clusters": risk_clusters,
            "spotlight_goals": spotlight_goals,
            "kpi_watch": kpi_watch,
        }

    def get_overview(self) -> dict[str, Any]:
        demo_employee = self.get_employee_workspace(self.demo_employee_id)
        dashboard = self.get_dashboard()
        return {
            "app_name": settings.app_name,
            "llm_mode": self.llm.provider_name,
            "demo_employee_id": self.demo_employee_id,
            "dataset": {
                "employees": int(len(self.employee_index)),
                "goals": int(len(self.goal_index)),
                "documents": int(len(self.documents)),
                "events": int(len(self.goal_events)),
                "reviews": int(len(self.goal_reviews)),
            },
            "hero_metrics": [
                {
                    "label": "Средний quality index",
                    "value": f"{dashboard['summary']['avg_smart_score'] * 100:.0f}%",
                },
                {
                    "label": "Стратегическая связка",
                    "value": f"{dashboard['summary']['alignment_coverage'] * 100:.0f}%",
                },
                {
                    "label": "Activity-based goals",
                    "value": f"{dashboard['summary']['activity_goal_share'] * 100:.0f}%",
                },
            ],
            "featured_employee": demo_employee["employee"],
            "featured_health": demo_employee["health"],
            "cache_hit": self.cache_hit,
        }
