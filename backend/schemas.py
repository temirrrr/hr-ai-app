from typing import List, Optional

from pydantic import BaseModel, Field


class SmartEvaluation(BaseModel):
    specific: str
    measurable: str
    achievable: str
    relevant: str
    time_bound: str
    score: float
    recommendation: List[str] = Field(default_factory=list)
    improved_version: str


class SimilarGoal(BaseModel):
    goal_id: str
    goal_text: str
    employee_name: Optional[str] = None
    status: str
    similarity: float


class EvidenceItem(BaseModel):
    doc_id: str
    title: str
    doc_type: str
    source_quote: str
    keywords: List[str] = Field(default_factory=list)
    similarity: float
    department_fit: bool


class GoalSetHealth(BaseModel):
    goal_count: int
    weight_total: float
    period: dict
    issues: List[str] = Field(default_factory=list)
    status: str


class GoalInsights(BaseModel):
    alignment_score: float
    alignment_level: str
    goal_type: str
    duplicate_risk: str
    weaknesses: List[str] = Field(default_factory=list)
    similar_goals: List[SimilarGoal] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    set_health: GoalSetHealth
    llm_mode: str


class GoalAssessmentRequest(BaseModel):
    goal_text: str
    employee_id: Optional[int] = None
    focus_priority: Optional[str] = None
    metric: Optional[str] = None
    deadline: Optional[str] = None


class GoalAssessmentResponse(BaseModel):
    evaluation: SmartEvaluation
    insights: GoalInsights


class ProjectCard(BaseModel):
    project_id: str
    project_code: str
    project_name: str
    role: str
    allocation_percent: Optional[int] = None
    status: str
    description: str


class KPIHighlight(BaseModel):
    metric_key: str
    title: str
    value: float
    unit: str
    scope_type: str


class GoalCard(BaseModel):
    goal_id: str
    goal_text: str
    status: str
    weight: Optional[float] = None
    smart_score: float
    alignment_level: str
    goal_type: str
    review_comment: str = ""


class IssueCard(BaseModel):
    label: str
    count: int


class EmployeeBrief(BaseModel):
    employee_id: int
    full_name: str
    department: str
    position: str
    manager_name: Optional[str] = None


class EmployeeSearchItem(BaseModel):
    id: int
    full_name: str
    employee_code: str
    department_name: str
    position_name: str


class EmployeeHealth(BaseModel):
    goal_count: int
    weight_total: float
    period: dict
    issues: List[str] = Field(default_factory=list)
    status: str
    avg_smart_score: float
    approved_share: float
    completed_share: float


class EmployeeProfile(EmployeeBrief):
    email: str
    tenure_years: float


class EmployeeWorkspaceResponse(BaseModel):
    employee: EmployeeProfile
    period: dict
    health: EmployeeHealth
    projects: List[ProjectCard] = Field(default_factory=list)
    manager_goals: List[dict] = Field(default_factory=list)
    documents: List[EvidenceItem] = Field(default_factory=list)
    kpis: List[KPIHighlight] = Field(default_factory=list)
    current_goals: List[GoalCard] = Field(default_factory=list)
    top_issues: List[IssueCard] = Field(default_factory=list)


class GoalProposal(BaseModel):
    goal_text: str
    source_document: str
    source_quote: str
    smart_score: float
    alignment_score: float
    alignment_level: str
    goal_type: str
    context_reasoning: str
    recommendations: List[str] = Field(default_factory=list)
    improved_version: str


class GoalGenerationRequest(BaseModel):
    employee_id: int
    focus_priority: Optional[str] = None
    count: int = 4


class GoalGenerationResponse(BaseModel):
    employee: EmployeeBrief
    period: dict
    proposals: List[GoalProposal] = Field(default_factory=list)
    sources: List[EvidenceItem] = Field(default_factory=list)
    llm_mode: str


class DepartmentRanking(BaseModel):
    department_name: str
    goals: int
    avg_smart_score: float
    avg_alignment: float
    risk_band: str
    headline: str


class RiskCluster(BaseModel):
    label: str
    count: int


class SpotlightGoal(BaseModel):
    goal_id: str
    goal_text: str
    department_name: str
    smart_score: float
    alignment_score: float


class DashboardSummary(BaseModel):
    employees: int
    goals: int
    documents: int
    avg_smart_score: float
    alignment_coverage: float
    activity_goal_share: float


class DashboardKPI(BaseModel):
    title: str
    value: float
    unit: str
    scope_type: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    period: dict | None = None
    department_rankings: List[DepartmentRanking] = Field(default_factory=list)
    risk_clusters: List[RiskCluster] = Field(default_factory=list)
    spotlight_goals: List[SpotlightGoal] = Field(default_factory=list)
    kpi_watch: List[DashboardKPI] = Field(default_factory=list)


class MetricTile(BaseModel):
    label: str
    value: str


class DatasetSnapshot(BaseModel):
    employees: int
    goals: int
    documents: int
    events: int
    reviews: int


class OverviewResponse(BaseModel):
    app_name: str
    llm_mode: str
    demo_employee_id: int
    cache_hit: bool = False
    dataset: DatasetSnapshot
    hero_metrics: List[MetricTile] = Field(default_factory=list)
    featured_employee: EmployeeProfile
    featured_health: EmployeeHealth
