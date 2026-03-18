import { startTransition, useDeferredValue, useEffect, useRef, useState } from 'react'
import './App.css'
import {
  Activity,
  ArrowRight,
  Bot,
  BrainCircuit,
  Building2,
  CheckCircle2,
  Clock3,
  FileSearch,
  Layers3,
  Network,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TriangleAlert,
  Users,
  WandSparkles,
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001/api'

type MetricTile = {
  label: string
  value: string
}

type EmployeeProfile = {
  employee_id: number
  full_name: string
  department: string
  position: string
  manager_name?: string | null
  email?: string
  tenure_years?: number
}

type EmployeeSearchItem = {
  id: number
  full_name: string
  employee_code: string
  department_name: string
  position_name: string
}

type EvidenceItem = {
  doc_id: string
  title: string
  doc_type: string
  source_quote: string
  keywords: string[]
  similarity: number
  department_fit: boolean
}

type GoalCard = {
  goal_id: string
  goal_text: string
  status: string
  weight?: number | null
  smart_score: number
  alignment_level: string
  goal_type: string
  review_comment: string
}

type KPIHighlight = {
  metric_key: string
  title: string
  value: number
  unit: string
  scope_type: string
}

type ProjectCard = {
  project_id: string
  project_code: string
  project_name: string
  role: string
  allocation_percent?: number | null
  status: string
  description: string
}

type IssueCard = {
  label: string
  count: number
}

type Health = {
  goal_count: number
  weight_total: number
  period: { year: number; quarter: string }
  issues: string[]
  status: string
  avg_smart_score: number
  approved_share: number
  completed_share: number
}

type OverviewResponse = {
  app_name: string
  llm_mode: string
  demo_employee_id: number
  cache_hit?: boolean
  dataset: {
    employees: number
    goals: number
    documents: number
    events: number
    reviews: number
  }
  hero_metrics: MetricTile[]
  featured_employee: EmployeeProfile
  featured_health: Health
}

type WorkspaceResponse = {
  employee: EmployeeProfile
  period: { year: number; quarter: string }
  health: Health
  projects: ProjectCard[]
  manager_goals: Array<{ goal_id: string; goal_text: string; status: string; weight?: number | null }>
  documents: EvidenceItem[]
  kpis: KPIHighlight[]
  current_goals: GoalCard[]
  top_issues: IssueCard[]
}

type EvaluationResponse = {
  evaluation: {
    specific: string
    measurable: string
    achievable: string
    relevant: string
    time_bound: string
    score: number
    recommendation: string[]
    improved_version: string
  }
  insights: {
    alignment_score: number
    alignment_level: string
    goal_type: string
    duplicate_risk: string
    weaknesses: string[]
    similar_goals: Array<{
      goal_id: string
      goal_text: string
      employee_name?: string
      status: string
      similarity: number
    }>
    evidence: EvidenceItem[]
    set_health: {
      goal_count: number
      weight_total: number
      issues: string[]
      period: { year: number; quarter: string }
      status: string
    }
    llm_mode: string
  }
}

type GoalProposal = {
  goal_text: string
  source_document: string
  source_quote: string
  smart_score: number
  alignment_score: number
  alignment_level: string
  goal_type: string
  context_reasoning: string
  recommendations: string[]
  improved_version: string
}

type GenerationResponse = {
  employee: EmployeeProfile
  period: { year: number; quarter: string }
  proposals: GoalProposal[]
  sources: EvidenceItem[]
  llm_mode: string
}

type DashboardResponse = {
  summary: {
    employees: number
    goals: number
    documents: number
    avg_smart_score: number
    alignment_coverage: number
    activity_goal_share: number
  }
  period?: { year: number; quarter: string }
  department_rankings: Array<{
    department_name: string
    goals: number
    avg_smart_score: number
    avg_alignment: number
    risk_band: string
    headline: string
  }>
  risk_clusters: Array<{ label: string; count: number }>
  spotlight_goals: Array<{
    goal_id: string
    goal_text: string
    department_name: string
    smart_score: number
    alignment_score: number
  }>
  kpi_watch: Array<{ title: string; value: number; unit: string; scope_type: string }>
}

function pct(value: number) {
  return `${Math.round((value || 0) * 100)}%`
}

function scoreTone(score: number) {
  if (score >= 0.78) return 'good'
  if (score >= 0.55) return 'watch'
  return 'risk'
}

function humanizeToken(value: string) {
  return value.replace(/_/g, ' ').trim()
}

function displayGoalType(value?: string) {
  switch (value) {
    case 'impact-based':
      return 'влияние'
    case 'output-based':
      return 'результат'
    case 'activity-based':
      return 'активность'
    default:
      return value ? humanizeToken(value) : 'не определён'
  }
}

function displayAlignmentLevel(value?: string) {
  switch (value) {
    case 'strategic':
      return 'стратегическая'
    case 'functional':
      return 'функциональная'
    case 'operational':
      return 'операционная'
    default:
      return value ? humanizeToken(value) : 'не определена'
  }
}

function displayStatus(value?: string) {
  switch (value) {
    case 'approved':
      return 'утверждена'
    case 'submitted':
      return 'на согласовании'
    case 'in_progress':
      return 'в работе'
    case 'done':
      return 'завершена'
    case 'draft':
      return 'черновик'
    case 'cancelled':
      return 'отменена'
    case 'rejected':
      return 'отклонена'
    default:
      return value ? humanizeToken(value) : 'статус не задан'
  }
}

function displayScopeType(value?: string) {
  switch (value) {
    case 'company':
      return 'компания'
    case 'department':
      return 'подразделение'
    case 'employee':
      return 'сотрудник'
    default:
      return value ? humanizeToken(value) : 'источник не указан'
  }
}

function displayDuplicateRisk(value?: string) {
  switch (value) {
    case 'high':
      return 'высокий'
    case 'medium':
      return 'средний'
    case 'low':
      return 'низкий'
    default:
      return value ? humanizeToken(value) : 'не определён'
  }
}

function displayIssueLabel(value: string) {
  if (value === 'Activity-based') return 'цели-активности'
  return value
}

function displayHeroMetricLabel(value: string) {
  switch (value) {
    case 'Средний quality index':
      return 'Средний индекс качества'
    case 'Activity-based goals':
      return 'Доля целей-активностей'
    default:
      return value
  }
}

function displayLlmMode(value?: string) {
  if (!value) return 'загрузка'
  if (value === 'Rule Engine') return 'Rule Engine + RAG'
  return value
}

function Gauge({ score, label, caption }: { score: number; label: string; caption: string }) {
  const angle = Math.max(0, Math.min(100, Math.round(score * 100)))
  return (
    <div className="gauge-card">
      <div
        className="gauge-ring"
        style={{ background: `conic-gradient(var(--accent) ${angle}%, rgba(255,255,255,0.06) ${angle}% 100%)` }}
      >
        <div className="gauge-core">
          <strong>{angle}%</strong>
          <span>{label}</span>
        </div>
      </div>
      <p>{caption}</p>
    </div>
  )
}

function App() {
  const studioRef = useRef<HTMLElement | null>(null)
  const [overview, setOverview] = useState<OverviewResponse | null>(null)
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [employees, setEmployees] = useState<EmployeeSearchItem[]>([])
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null)
  const [employeeSearch, setEmployeeSearch] = useState('')
  const deferredSearch = useDeferredValue(employeeSearch)

  const [goalText, setGoalText] = useState('')
  const [goalMetric, setGoalMetric] = useState('')
  const [goalDeadline, setGoalDeadline] = useState('')
  const [focusPriority, setFocusPriority] = useState('снижение затрат и надёжность сервисов')
  const [proposalCount, setProposalCount] = useState(4)

  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null)
  const [generation, setGeneration] = useState<GenerationResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState({
    overview: true,
    workspace: false,
    evaluate: false,
    generate: false,
  })

  const fetchEvaluation = async (payload: {
    goal_text: string
    employee_id: number | null
    focus_priority: string
    metric?: string
    deadline?: string
  }) => {
    const response = await fetch(`${API_BASE}/goals/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      throw new Error('evaluation_failed')
    }
    return (await response.json()) as EvaluationResponse
  }

  const fetchGeneration = async (payload: {
    employee_id: number
    focus_priority: string
    count: number
  }) => {
    const response = await fetch(`${API_BASE}/goals/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      throw new Error('generation_failed')
    }
    return (await response.json()) as GenerationResponse
  }

  useEffect(() => {
    const loadInitial = async () => {
      try {
        const [overviewRes, dashboardRes] = await Promise.all([
          fetch(`${API_BASE}/overview`),
          fetch(`${API_BASE}/dashboard`),
        ])
        if (!overviewRes.ok || !dashboardRes.ok) {
          throw new Error('bootstrap_failed')
        }
        const overviewData: OverviewResponse = await overviewRes.json()
        const dashboardData: DashboardResponse = await dashboardRes.json()
        startTransition(() => {
          setOverview(overviewData)
          setDashboard(dashboardData)
          setSelectedEmployeeId(overviewData.demo_employee_id)
        })
      } catch {
        setError('Не удалось загрузить командный центр. Проверь backend на `localhost:8001`.')
      } finally {
        setLoading((state) => ({ ...state, overview: false }))
      }
    }

    loadInitial()
  }, [])

  useEffect(() => {
    const loadEmployees = async () => {
      try {
        const response = await fetch(`${API_BASE}/employees?q=${encodeURIComponent(deferredSearch)}&limit=12`)
        if (!response.ok) {
          throw new Error('employees_failed')
        }
        const data: EmployeeSearchItem[] = await response.json()
        startTransition(() => setEmployees(data))
      } catch {
        setEmployees([])
      }
    }

    loadEmployees()
  }, [deferredSearch])

  useEffect(() => {
    if (!selectedEmployeeId) return
    let active = true

    const loadWorkspace = async () => {
      setError('')
      setLoading((state) => ({ ...state, workspace: true, evaluate: true, generate: true }))
      try {
        const response = await fetch(`${API_BASE}/employees/${selectedEmployeeId}/workspace`)
        if (!response.ok) {
          throw new Error('workspace_failed')
        }
        const data: WorkspaceResponse = await response.json()
        const initialGoal = data.current_goals[0]?.goal_text ?? ''

        if (!active) return
        startTransition(() => {
          setWorkspace(data)
          setGoalText(initialGoal)
          setGoalMetric('')
          setGoalDeadline('')
          setEvaluation(null)
          setGeneration(null)
        })

        const [evaluationData, generationData] = await Promise.all([
          initialGoal
            ? fetchEvaluation({
                goal_text: initialGoal,
                employee_id: selectedEmployeeId,
                focus_priority: focusPriority,
              })
            : Promise.resolve(null),
          fetchGeneration({
            employee_id: selectedEmployeeId,
            focus_priority: focusPriority,
            count: proposalCount,
          }),
        ])

        if (!active) return
        startTransition(() => {
          if (evaluationData) setEvaluation(evaluationData)
          setGeneration(generationData)
        })
      } catch {
        setError('Не удалось загрузить профиль сотрудника.')
      } finally {
        if (!active) return
        setLoading((state) => ({ ...state, workspace: false, evaluate: false, generate: false }))
      }
    }

    loadWorkspace()

    return () => {
      active = false
    }
  }, [selectedEmployeeId])

  const handleEvaluate = async () => {
    if (!goalText.trim()) return
    setLoading((state) => ({ ...state, evaluate: true }))
    setError('')
    try {
      const data = await fetchEvaluation({
        goal_text: goalText,
        employee_id: selectedEmployeeId,
        focus_priority: focusPriority,
        metric: goalMetric || undefined,
        deadline: goalDeadline || undefined,
      })
      startTransition(() => setEvaluation(data))
    } catch {
      setError('Оценка цели не выполнена.')
    } finally {
      setLoading((state) => ({ ...state, evaluate: false }))
    }
  }

  const handleGenerate = async () => {
    if (!selectedEmployeeId) return
    setLoading((state) => ({ ...state, generate: true }))
    setError('')
    try {
      const data = await fetchGeneration({
        employee_id: selectedEmployeeId,
        focus_priority: focusPriority,
        count: proposalCount,
      })
      startTransition(() => setGeneration(data))
    } catch {
      setError('Не удалось сгенерировать цели.')
    } finally {
      setLoading((state) => ({ ...state, generate: false }))
    }
  }

  const adoptProposal = async (proposal: GoalProposal) => {
    startTransition(() => {
      setGoalText(proposal.goal_text)
      setGoalMetric('')
      setGoalDeadline('')
      setEvaluation(null)
    })
    studioRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setLoading((state) => ({ ...state, evaluate: true }))
    setError('')
    try {
      const data = await fetchEvaluation({
        goal_text: proposal.goal_text,
        employee_id: selectedEmployeeId,
        focus_priority: focusPriority,
      })
      startTransition(() => setEvaluation(data))
    } catch {
      setError('Не удалось пересчитать оценку для выбранного предложения.')
    } finally {
      setLoading((state) => ({ ...state, evaluate: false }))
    }
  }

  const featuredName = workspace?.employee.full_name ?? overview?.featured_employee.full_name ?? 'AI Workspace'
  const smartBreakdown = [
    ['Конкретность', evaluation?.evaluation.specific],
    ['Измеримость', evaluation?.evaluation.measurable],
    ['Достижимость', evaluation?.evaluation.achievable],
    ['Связь с приоритетом', evaluation?.evaluation.relevant],
    ['Срок', evaluation?.evaluation.time_bound],
  ] as const
  const recommendations = (evaluation?.evaluation.recommendation?.length
    ? evaluation.evaluation.recommendation
    : workspace?.health.issues ?? []
  ).slice(0, 3)
  const evidenceItems = (evaluation?.insights.evidence ?? workspace?.documents ?? []).slice(0, 2)
  const similarGoals = (evaluation?.insights.similar_goals ?? []).slice(0, 2)
  const proposalItems = generation?.proposals ?? []
  const departmentRankings = (dashboard?.department_rankings ?? []).slice(0, 4)
  const riskClusters = (dashboard?.risk_clusters ?? []).slice(0, 4)
  const kpiWatch = (dashboard?.kpi_watch ?? []).slice(0, 3)

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <div className="ambient ambient-c" />

      <div className="page">
        <header className="hero-panel fade-up">
          <div className="hero-copy">
            <div className="eyebrow">
              <Radar size={16} />
              KMG HR AI Command Center
            </div>
            <h1>{overview?.app_name ?? 'AI слой для победного Performance Management демо'}</h1>
            <p>
              Показывает не только SMART, а реальную стратегическую связку: ВНД, KPI,
              цели руководителя, качество набора целей и дашборд зрелости по подразделениям.
            </p>

            <div className="hero-metrics">
              {(overview?.hero_metrics ?? []).map((metric) => (
                <div key={metric.label} className="metric-tile">
                  <span>{displayHeroMetricLabel(metric.label)}</span>
                  <strong>{metric.value}</strong>
                </div>
              ))}
            </div>

            <div className="hero-status">
              <span className="pill pill-soft">
                <Bot size={14} />
                Режим AI: {displayLlmMode(overview?.llm_mode)}
              </span>
              <span className="pill pill-soft">
                <Clock3 size={14} />
                {overview?.cache_hit ? 'кэш прогрет' : 'холодный старт'}
              </span>
              <span className="pill pill-soft">
                <Users size={14} />
                {overview?.dataset.employees ?? 0} сотрудников
              </span>
              <span className="pill pill-soft">
                <FileSearch size={14} />
                {overview?.dataset.documents ?? 0} ВНД
              </span>
            </div>
          </div>

          <div className="hero-spotlight">
            <Gauge
              score={workspace?.health.avg_smart_score ?? overview?.featured_health.avg_smart_score ?? 0}
              label="индекс"
              caption={`Фокусный сотрудник: ${featuredName}`}
            />
            <div className="spotlight-card">
              <div className="spotlight-line">
                <span>Набор целей</span>
                <strong>{workspace?.health.goal_count ?? overview?.featured_health.goal_count ?? 0}</strong>
              </div>
              <div className="spotlight-line">
                <span>Вес целей</span>
                <strong>{workspace?.health.weight_total ?? overview?.featured_health.weight_total ?? 0}%</strong>
              </div>
              <div className="spotlight-line">
                <span>Утверждено / активно</span>
                <strong>{pct(workspace?.health.approved_share ?? overview?.featured_health.approved_share ?? 0)}</strong>
              </div>
              <div className="spotlight-line">
                <span>Завершено</span>
                <strong>{pct(workspace?.health.completed_share ?? overview?.featured_health.completed_share ?? 0)}</strong>
              </div>
            </div>
          </div>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        <main className="workspace-grid">
          <aside className="panel control-panel fade-up">
            <div className="panel-head">
              <div>
                <span className="panel-tag">1. Контекст сотрудника</span>
                <h2>Кого выводим на сцену</h2>
              </div>
              <ShieldCheck size={18} />
            </div>

            <label className="search-box">
              <Search size={16} />
              <input
                value={employeeSearch}
                onChange={(event) => setEmployeeSearch(event.target.value)}
                placeholder="Найти сотрудника, отдел или роль"
              />
            </label>

            <div className="employee-list">
              {employees.map((employee) => (
                <button
                  key={employee.id}
                  type="button"
                  className={`employee-card ${selectedEmployeeId === employee.id ? 'active' : ''}`}
                  onClick={() => setSelectedEmployeeId(employee.id)}
                >
                  <strong>{employee.full_name}</strong>
                  <span>{employee.position_name}</span>
                  <small>{employee.department_name}</small>
                </button>
              ))}
            </div>

            <div className="profile-block">
              <div className="profile-title">
                <Building2 size={18} />
                <div>
                  <strong>{workspace?.employee.full_name ?? 'Загрузка профиля...'}</strong>
                  <span>
                    {workspace?.employee.position ?? '...'} · {workspace?.employee.department ?? '...'}
                  </span>
                </div>
              </div>
              <div className="detail-grid">
                <div>
                  <span>Руководитель</span>
                  <strong>{workspace?.employee.manager_name ?? 'Не указан'}</strong>
                </div>
                <div>
                  <span>Стаж</span>
                  <strong>{workspace?.employee.tenure_years ?? 0} лет</strong>
                </div>
                <div>
                  <span>Период</span>
                  <strong>
                    {workspace?.period.quarter ?? 'Q?'} {workspace?.period.year ?? '----'}
                  </strong>
                </div>
                <div>
                  <span>Набор целей</span>
                  <strong>{workspace?.health.goal_count ?? 0} целей</strong>
                </div>
              </div>
            </div>

            <div className="subpanel">
              <div className="subpanel-head">
                <Layers3 size={16} />
                Активные проекты
              </div>
              <div className="stack-list">
                {(workspace?.projects ?? []).slice(0, 3).map((project) => (
                  <div key={project.project_id} className="mini-card">
                    <strong>{project.project_name}</strong>
                    <span>
                      {project.role}
                      {project.allocation_percent ? ` · ${project.allocation_percent}%` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="subpanel">
              <div className="subpanel-head">
                <Network size={16} />
                KPI и каскад
              </div>
              <div className="stack-list">
                {(workspace?.kpis ?? []).slice(0, 3).map((kpi) => (
                  <div key={kpi.metric_key} className="mini-card">
                    <strong>
                      {kpi.title}: {kpi.value} {kpi.unit}
                    </strong>
                    <span>{kpi.scope_type === 'company' ? 'Сигнал компании' : 'Сигнал подразделения'}</span>
                  </div>
                ))}
                {(workspace?.manager_goals ?? []).slice(0, 2).map((goal) => (
                  <div key={goal.goal_id} className="mini-card mini-card-accent">
                    <strong>Каскад цели руководителя</strong>
                    <span>{goal.goal_text}</span>
                  </div>
                ))}
              </div>
            </div>
          </aside>

          <section ref={studioRef} className="panel studio-panel fade-up">
            <div className="panel-head">
              <div>
                <span className="panel-tag">2. Goal Studio</span>
                <h2>Проверка и генерация целей</h2>
              </div>
              <BrainCircuit size={18} />
            </div>

            <div className="studio-form">
              <div className="field">
                <label>Фокус периода</label>
                <input
                  value={focusPriority}
                  onChange={(event) => setFocusPriority(event.target.value)}
                  placeholder="Например: снижение затрат, reliability, цифровизация"
                />
              </div>

              <div className="field">
                <label>Черновик цели</label>
                <textarea
                  value={goalText}
                  onChange={(event) => setGoalText(event.target.value)}
                  placeholder="Сформулируй цель сотрудника. AI разложит её по SMART, стратегической связке и рискам."
                />
              </div>

              <div className="field-row">
                <div className="field">
                  <label>Подсказка по метрике</label>
                  <input
                    value={goalMetric}
                    onChange={(event) => setGoalMetric(event.target.value)}
                    placeholder="SLA compliance / MTTR / defect rate"
                  />
                </div>
                <div className="field">
                  <label>Подсказка по сроку</label>
                  <input
                    value={goalDeadline}
                    onChange={(event) => setGoalDeadline(event.target.value)}
                    placeholder="до конца Q3 2025"
                  />
                </div>
              </div>

              <div className="actions-row">
                <button type="button" className="button primary" onClick={handleEvaluate} disabled={loading.evaluate}>
                  {loading.evaluate ? <span className="loader" /> : <Target size={16} />}
                  Проверить цель
                </button>

                <div className="generator-inline">
                  <select
                    value={proposalCount}
                    onChange={(event) => setProposalCount(Number(event.target.value))}
                  >
                    <option value={3}>3 цели</option>
                    <option value={4}>4 цели</option>
                    <option value={5}>5 целей</option>
                  </select>
                  <button type="button" className="button secondary" onClick={handleGenerate} disabled={loading.generate}>
                    {loading.generate ? <span className="loader" /> : <WandSparkles size={16} />}
                    Сгенерировать пакет
                  </button>
                </div>
              </div>
            </div>

            <div className="evaluation-grid">
              <div className="evaluation-main">
                <div className="evaluation-head">
                  <Gauge
                    score={evaluation?.evaluation.score ?? workspace?.health.avg_smart_score ?? 0}
                    label="SMART"
                    caption="Оценка по правилам и контексту"
                  />
                  <div className="evaluation-summary">
                    <div className="signal-stack signal-stack-inline">
                      <div className={`signal-box ${scoreTone(evaluation?.insights.alignment_score ?? 0.55)}`}>
                        <span>Стратегическая связка</span>
                        <strong>{pct(evaluation?.insights.alignment_score ?? 0.55)}</strong>
                      </div>
                      <div className="signal-box neutral">
                        <span>Тип цели</span>
                        <strong>{displayGoalType(evaluation?.insights.goal_type)}</strong>
                      </div>
                      <div className={`signal-box ${evaluation?.insights.duplicate_risk === 'high' ? 'risk' : 'neutral'}`}>
                        <span>Риск дублирования</span>
                        <strong>{displayDuplicateRisk(evaluation?.insights.duplicate_risk)}</strong>
                      </div>
                    </div>

                    <div className="recommendation-strip">
                      {recommendations.length ? recommendations.map((item) => (
                        <div key={item} className="recommendation-row">
                          <CheckCircle2 size={15} />
                          <span>{item}</span>
                        </div>
                      )) : (
                        <div className="recommendation-row">
                          <CheckCircle2 size={15} />
                          <span>Рекомендации появятся после детальной оценки цели.</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="smart-grid">
                  {smartBreakdown.map(([label, text]) => (
                    <article key={label} className="smart-card">
                      <span>{label}</span>
                      <p>{text ?? (loading.evaluate ? 'AI анализирует текущую цель и собирает пояснение.' : 'Запусти оценку, чтобы увидеть разбор по критерию.')}</p>
                    </article>
                  ))}
                </div>

                <div className="rewrite-card">
                  <div className="rewrite-head">
                    <Sparkles size={16} />
                    Усиленная формулировка
                  </div>
                  <p>{evaluation?.evaluation.improved_version ?? (loading.evaluate ? 'Формируем улучшенную формулировку на основе текущей цели.' : 'Здесь появится усиленная формулировка.')}</p>
                </div>
              </div>

              <div className="evaluation-side">
                <div className="subpanel">
                  <div className="subpanel-head">
                    <FileSearch size={16} />
                    Подтверждение из ВНД
                  </div>
                  <div className="stack-list">
                    {evidenceItems.length ? evidenceItems.map((item) => (
                      <div key={item.doc_id} className="mini-card mini-card-accent">
                        <strong>{item.title}</strong>
                        <span>{item.source_quote}</span>
                      </div>
                    )) : (
                      <div className="mini-card mini-card-accent">
                        <span>Подберём подтверждение из ВНД после выбора цели или сотрудника.</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="subpanel">
                  <div className="subpanel-head">
                    <Activity size={16} />
                    Похожие цели
                  </div>
                  <div className="stack-list">
                    {similarGoals.length ? similarGoals.map((goal) => (
                      <div key={goal.goal_id} className="mini-card">
                        <strong>{goal.goal_text}</strong>
                        <span>
                          {goal.employee_name ? `${goal.employee_name} · ` : ''}
                          {displayStatus(goal.status)} · {pct(goal.similarity)}
                        </span>
                      </div>
                    )) : (
                      <div className="mini-card">
                        <span>Похожие формулировки появятся после оценки текущего черновика.</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="proposal-section">
              <div className="panel-head compact">
                <div>
                  <span className="panel-tag">3. AI-предложения</span>
                  <h3>Набор целей для роли</h3>
                </div>
                <WandSparkles size={18} />
              </div>

              <div className="proposal-grid">
                {proposalItems.length ? (
                  proposalItems.map((proposal, index) => (
                    <article key={`${proposal.goal_text}-${index}`} className="proposal-card">
                      <div className="proposal-top">
                        <span className={`score-chip ${scoreTone(proposal.smart_score)}`}>{pct(proposal.smart_score)}</span>
                        <span className="ghost-chip">{displayAlignmentLevel(proposal.alignment_level)}</span>
                      </div>
                      <h4>{proposal.goal_text}</h4>
                      <p>{proposal.context_reasoning}</p>
                      <div className="proposal-source">
                        <strong>{proposal.source_document}</strong>
                        <span>{proposal.source_quote}</span>
                      </div>
                      <div className="proposal-actions">
                        <button type="button" className="button tertiary" onClick={() => adoptProposal(proposal)}>
                          Взять в студию
                          <ArrowRight size={15} />
                        </button>
                      </div>
                    </article>
                  ))
                ) : loading.generate ? (
                  <div className="empty-state">
                    <WandSparkles size={24} />
                    <strong>AI собирает пакет целей</strong>
                    <p>Подтягиваем ВНД, KPI, каскад от руководителя и профиль сотрудника.</p>
                  </div>
                ) : (
                  <div className="empty-state">
                    <WandSparkles size={24} />
                    <strong>Сгенерируй пакет целей</strong>
                    <p>Мы соберём цели на основе ВНД, KPI, контекста сотрудника и каскада от руководителя.</p>
                  </div>
                )}
              </div>
            </div>
          </section>

          <aside className="panel radar-panel fade-up">
              <div className="panel-head">
                <div>
                  <span className="panel-tag">3. Радар команды</span>
                  <h2>Зрелость целеполагания</h2>
                </div>
                <TriangleAlert size={18} />
              </div>

            <div className="ghost-chip" style={{ marginBottom: '14px' }}>
              Срез: {dashboard?.period?.quarter ?? 'Q?'} {dashboard?.period?.year ?? '----'}
            </div>

            <div className="radar-summary">
              <div className="radar-stat">
                <span>Качество</span>
                <strong>{pct(dashboard?.summary.avg_smart_score ?? 0)}</strong>
              </div>
              <div className="radar-stat">
                <span>Связка</span>
                <strong>{pct(dashboard?.summary.alignment_coverage ?? 0)}</strong>
              </div>
              <div className="radar-stat">
                <span>Активность</span>
                <strong>{pct(dashboard?.summary.activity_goal_share ?? 0)}</strong>
              </div>
            </div>

            <div className="subpanel">
              <div className="subpanel-head">
                <Building2 size={16} />
                Лидеры подразделений
              </div>
              <div className="leaderboard">
                {departmentRankings.map((department) => (
                  <div key={department.department_name} className="leader-row">
                    <div className="leader-copy">
                      <strong>{department.department_name}</strong>
                      <span>{department.headline}</span>
                    </div>
                    <div className="leader-bar">
                      <div
                        className={`leader-fill ${department.risk_band}`}
                        style={{ width: pct(department.avg_smart_score) }}
                      />
                    </div>
                    <strong className="leader-score">{pct(department.avg_smart_score)}</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="subpanel">
              <div className="subpanel-head">
                <TriangleAlert size={16} />
                Кластеры рисков
              </div>
              <div className="risk-clusters">
                {riskClusters.map((cluster) => (
                  <div key={cluster.label} className="cluster-pill">
                    <span>{displayIssueLabel(cluster.label)}</span>
                    <strong>{cluster.count}</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="subpanel">
              <div className="subpanel-head">
                <Clock3 size={16} />
                Контроль KPI
              </div>
              <div className="stack-list">
                {kpiWatch.map((kpi) => (
                  <div key={`${kpi.title}-${kpi.scope_type}`} className="mini-card">
                    <strong>
                      {kpi.title}: {kpi.value} {kpi.unit}
                    </strong>
                    <span>{displayScopeType(kpi.scope_type)}</span>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </main>

        <section className="panel goal-board fade-up">
          <div className="panel-head compact">
            <div>
              <span className="panel-tag">4. Текущий портфель</span>
              <h3>Набор текущих целей сотрудника</h3>
            </div>
            <Users size={18} />
          </div>

          <div className="goal-board-grid">
            {(workspace?.current_goals ?? []).map((goal) => (
              <article key={goal.goal_id} className="goal-board-card">
                <div className="goal-board-top">
                  <span className={`score-chip ${scoreTone(goal.smart_score)}`}>{pct(goal.smart_score)}</span>
                  <span className="ghost-chip">{displayGoalType(goal.goal_type)}</span>
                </div>
                <h4>{goal.goal_text}</h4>
                <div className="goal-board-meta">
                  <span>{displayStatus(goal.status)}</span>
                  <span>{goal.weight ? `${goal.weight}%` : 'вес не задан'}</span>
                  <span>{displayAlignmentLevel(goal.alignment_level)}</span>
                </div>
                <p>{goal.review_comment || 'Комментарий руководителя пока не зафиксирован.'}</p>
              </article>
            ))}
          </div>

          <div className="issue-ribbon">
            {(workspace?.top_issues ?? []).map((issue) => (
              <div key={issue.label} className="issue-chip">
                <span>{issue.label}</span>
                <strong>{issue.count}</strong>
              </div>
            ))}
          </div>
        </section>

        {loading.overview || loading.workspace ? <div className="loading-line" /> : null}
      </div>
    </div>
  )
}

export default App
