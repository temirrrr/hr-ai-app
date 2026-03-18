from fastapi.testclient import TestClient

from main import app


def main() -> None:
    client = TestClient(app)
    checks = [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/api/overview"),
        ("GET", "/api/dashboard"),
        ("GET", "/api/employees?q=Шашкова&limit=3"),
        ("GET", "/api/employees/23/workspace"),
    ]
    for method, path in checks:
        response = client.request(method, path)
        print(method, path, response.status_code)
        response.raise_for_status()

    evaluate = client.post(
        "/api/goals/evaluate",
        json={
            "goal_text": "Сократить MTTR по критичным инцидентам на 15% до конца Q3 2025",
            "employee_id": 23,
        },
    )
    print("POST /api/goals/evaluate", evaluate.status_code)
    evaluate.raise_for_status()

    generate = client.post(
        "/api/goals/generate",
        json={
            "employee_id": 23,
            "focus_priority": "снижение затрат и надежность сервисов",
            "count": 3,
        },
    )
    print("POST /api/goals/generate", generate.status_code)
    generate.raise_for_status()


if __name__ == "__main__":
    main()
