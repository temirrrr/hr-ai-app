from services import HRCommandCenter


def main() -> None:
    service = HRCommandCenter()
    overview = service.get_overview()
    print("KMG HR AI Command Center warmup complete")
    print(f"LLM mode: {overview['llm_mode']}")
    print(f"Cache: {'hit' if service.cache_hit else 'miss'}")
    print(
        "Dataset:",
        f"{overview['dataset']['employees']} employees,",
        f"{overview['dataset']['goals']} goals,",
        f"{overview['dataset']['documents']} documents",
    )
    print(f"Demo employee id: {overview['demo_employee_id']}")


if __name__ == "__main__":
    main()
