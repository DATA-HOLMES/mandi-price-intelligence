"""Run Phase 1 in order: ingestion -> cleaning -> reconcile -> load.

Each stage is added here as it is built. Until then this script only
lists the planned stages.
"""


def main() -> None:
    """Run each Phase 1 stage in order."""
    stages = ["ingestion", "cleaning", "reconcile", "load"]
    for stage in stages:
        print(f"[not yet implemented] {stage}")


if __name__ == "__main__":
    main()