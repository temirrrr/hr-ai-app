from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_service
from schemas import (
    DashboardResponse,
    EmployeeSearchItem,
    EmployeeWorkspaceResponse,
    GoalAssessmentRequest,
    GoalAssessmentResponse,
    GoalGenerationRequest,
    GoalGenerationResponse,
    OverviewResponse,
)
from services import HRCommandCenter

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def overview(service: HRCommandCenter = Depends(get_service)) -> OverviewResponse:
    return OverviewResponse(**service.get_overview())


@router.get("/employees", response_model=list[EmployeeSearchItem])
def employees(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=12, ge=1, le=30),
    service: HRCommandCenter = Depends(get_service),
) -> list[EmployeeSearchItem]:
    return [EmployeeSearchItem(**item) for item in service.search_employees(query=q, limit=limit)]


@router.get("/employees/{employee_id}/workspace", response_model=EmployeeWorkspaceResponse)
def employee_workspace(
    employee_id: int,
    service: HRCommandCenter = Depends(get_service),
) -> EmployeeWorkspaceResponse:
    try:
        return EmployeeWorkspaceResponse(**service.get_employee_workspace(employee_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(service: HRCommandCenter = Depends(get_service)) -> DashboardResponse:
    return DashboardResponse(**service.get_dashboard())


@router.post("/goals/evaluate", response_model=GoalAssessmentResponse)
def evaluate_goal(
    request: GoalAssessmentRequest,
    service: HRCommandCenter = Depends(get_service),
) -> GoalAssessmentResponse:
    return GoalAssessmentResponse(
        **service.evaluate_goal(
            goal_text=request.goal_text,
            employee_id=request.employee_id,
            focus_priority=request.focus_priority,
            metric=request.metric,
            deadline=request.deadline,
        )
    )


@router.post("/goals/generate", response_model=GoalGenerationResponse)
def generate_goals(
    request: GoalGenerationRequest,
    service: HRCommandCenter = Depends(get_service),
) -> GoalGenerationResponse:
    try:
        return GoalGenerationResponse(
            **service.generate_goals(
                employee_id=request.employee_id,
                focus_priority=request.focus_priority,
                count=request.count,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/evaluate", response_model=GoalAssessmentResponse)
def evaluate_goal_legacy(
    request: GoalAssessmentRequest,
    service: HRCommandCenter = Depends(get_service),
) -> GoalAssessmentResponse:
    return evaluate_goal(request, service)


@router.post("/generate", response_model=GoalGenerationResponse)
def generate_goals_legacy(
    request: GoalGenerationRequest,
    service: HRCommandCenter = Depends(get_service),
) -> GoalGenerationResponse:
    return generate_goals(request, service)
