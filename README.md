# KMG HR AI Command Center

Хакатонная версия AI-слоя для `Performance Management`, заточенная под сильное демо:

- `Employee workspace`: контекст сотрудника, проекты, KPI, цели руководителя, health набора целей
- `Goal lab`: SMART + strategic alignment + duplicate risk + improved wording
- `AI generation`: цели на основе ВНД, KPI и каскада от руководителя
- `Team radar`: дашборд зрелости целеполагания по подразделениям

Проект работает на локальных CSV из `data/` и не зависит от внешней БД. Внешний LLM опционален: без ключа система работает на rule-based / retrieval логике, а с ключом улучшает формулировки и generation quality.

## Стек

- Backend: FastAPI, pandas, scikit-learn, OpenAI SDK
- Frontend: React 19, Vite, TypeScript
- Data intelligence: TF-IDF retrieval, rule engine, hybrid LLM orchestration

## Структура репозитория

- `backend/` — API, retrieval, scoring, generation
- `frontend/` — demo UI
- `data/` — хакатонный CSV-датасет
- `instructions/` — исходные инструкции и материалы кейса
- `presentation/` — финальные материалы для Demo Day

## Запуск

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# опционально: положить .env из .env.example
cp .env.example .env

# прогрев индексов и проверка датасета
python ingest_docs.py

# быстрый API smoke-test
python smoke_test.py

uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend ожидает backend на `http://localhost:8001`.
При необходимости можно переопределить API URL через `VITE_API_BASE_URL`.

## Опциональный внешний LLM

В `backend/.env`:

```env
LLM_API_KEY=your_key
LLM_MODEL=gpt-4.1-mini
# для OpenRouter / совместимого провайдера
# LLM_BASE_URL=https://openrouter.ai/api/v1
```

Если ключ не задан, backend не падает и остаётся полностью работоспособным.

## API

- `GET /api/overview`
- `GET /api/employees?q=...`
- `GET /api/employees/{employee_id}/workspace`
- `POST /api/goals/evaluate`
- `POST /api/goals/generate`
- `GET /api/dashboard`

## Demo flow для защиты

1. Открыть командный центр и показать `Team radar` по подразделениям.
2. Выбрать сильного demo-сотрудника из левой панели.
3. Показать его текущий набор целей и health набора.
4. Прогнать одну слабую цель через `Goal lab` и показать improved wording.
5. Сгенерировать пакет новых целей по фокусу квартала.
6. Взять один AI proposal обратно в `Goal lab` и показать, что контур замкнут.
