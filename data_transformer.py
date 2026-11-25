import csv
import json
import os
from datetime import datetime

DEFAULT_INPUT = "records.json"
DEFAULT_OUTPUT = "normalized_records.csv"
REQUIRED_FIELDS = ("id", "name", "score", "active")


def create_sample_input(filepath=DEFAULT_INPUT):
    sample_records = [
        {"id": 101, "name": "  Aarav Sharma ", "score": "88.5", "active": True, "role": "analyst"},
        {"id": "102", "name": "Meera Nair", "score": 94, "active": "false"},
        {"id": "bad_id", "name": "Invalid ID Row", "score": 75, "active": True},
        {"id": 104, "name": "", "score": 81, "active": True},
        {"id": 105, "name": "Kabir Verma", "score": 150, "active": True},
    ]
    temp_file = f"{filepath}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(sample_records, f, indent=2)
    os.replace(temp_file, filepath)


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise ValueError("Expected boolean or 'true'/'false'")


def validate_and_normalize_record(raw_record, row_index):
    if not isinstance(raw_record, dict):
        raise ValueError(f"Row {row_index}: Record must be a JSON object.")

    missing = [field for field in REQUIRED_FIELDS if field not in raw_record]
    if missing:
        raise ValueError(f"Row {row_index}: Missing required fields: {', '.join(missing)}")

    raw_id = raw_record["id"]
    if isinstance(raw_id, bool) or not str(raw_id).strip().isdigit():
        raise ValueError(f"Row {row_index}: 'id' must be a positive integer, got {raw_id!r}.")
    record_id = int(str(raw_id).strip())
    if record_id <= 0:
        raise ValueError(f"Row {row_index}: 'id' must be greater than 0.")

    name = str(raw_record["name"]).strip()
    if not name:
        raise ValueError(f"Row {row_index}: 'name' cannot be empty.")

    try:
        score = float(raw_record["score"])
    except (ValueError, TypeError):
        raise ValueError(f"Row {row_index}: 'score' must be numeric, got {raw_record['score']!r}.")
    if not (0.0 <= score <= 100.0):
        raise ValueError(f"Row {row_index}: 'score' must be between 0 and 100, got {score}.")

    try:
        active = parse_bool(raw_record["active"])
    except ValueError as exc:
        raise ValueError(f"Row {row_index}: 'active' invalid ({exc}).")

    tag = str(raw_record.get("role", "general")).strip().lower() or "general"

    return {
        "id": record_id,
        "name": name,
        "score": round(score, 2),
        "active": active,
        "tag": tag,
    }


def load_json_records(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Top-level JSON structure must be a list of objects.")
    return data


def write_csv_atomic(rows, output_path):
    fieldnames = ["id", "name", "score", "active", "tag"]
    temp_path = f"{output_path}.tmp"
    with open(temp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_path, output_path)


def run_pipeline(input_path, output_path):
    raw_items = load_json_records(input_path)
    valid_rows = []
    errors = []

    for idx, item in enumerate(raw_items, start=1):
        try:
            valid_rows.append(validate_and_normalize_record(item, idx))
        except ValueError as err:
            errors.append(str(err))

    write_csv_atomic(valid_rows, output_path)

    return {
        "total_seen": len(raw_items),
        "valid_count": len(valid_rows),
        "error_count": len(errors),
        "errors": errors,
        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def print_report(report, output_path):
    print("\n=== Pipeline Execution Report ===")
    print(f"Timestamp : {report['processed_at']}")
    print(f"Total Read: {report['total_seen']}")
    print(f"Valid Rows: {report['valid_count']}")
    print(f"Rejected  : {report['error_count']}")
    print(f"Output CSV: {output_path}")

    if report["errors"]:
        print("\nValidation Issues:")
        for msg in report["errors"]:
            print(f"  - {msg}")


def main():
    while True:
        print("\n=== JSON Schema Validator & CSV Transformer ===")
        print("1. Generate Sample Input (records.json)")
        print("2. Run Transformation Pipeline")
        print("3. Exit")

        choice = input("Choose an option (1-3): ").strip()
        if choice == "1":
            target = input(f"Sample file path [{DEFAULT_INPUT}]: ").strip() or DEFAULT_INPUT
            try:
                create_sample_input(target)
                print(f"Created sample input at '{target}' with valid and invalid test rows.")
            except OSError as exc:
                print(f"File error: {exc}")
        elif choice == "2":
            in_file = input(f"Input JSON file [{DEFAULT_INPUT}]: ").strip() or DEFAULT_INPUT
            out_file = input(f"Output CSV file [{DEFAULT_OUTPUT}]: ").strip() or DEFAULT_OUTPUT
            try:
                report = run_pipeline(in_file, out_file)
                print_report(report, out_file)
            except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as exc:
                print(f"Pipeline failed: {exc}")
        elif choice == "3":
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid option. Choose 1 to 3.")


if __name__ == "__main__":
    main()
