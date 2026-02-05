from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, request, send_file

from shift_logic import JobConfig, Person, generate_shift, validate_inputs

app = Flask(__name__)


def _load_people_from_excel(excel_path: Path):
    df = pd.read_excel(excel_path)
    time_cols = [c for c in df.columns if isinstance(c, str) and "-" in c]
    people = []
    for _, row in df.iterrows():
        availability = {t: str(row.get(t, "")).strip() == "〇" for t in time_cols}
        people.append(
            Person(
                name=str(row.get("名前", "")).strip(),
                grade=int(row.get("学年", 0)),
                committee=str(row.get("所属委員会", "")).strip(),
                availability=availability,
            )
        )
    return people, time_cols


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=None, errors=None, warnings=None)


@app.route("/generate", methods=["POST"])
def generate():
    excel_path = Path("namesheet.xlsx")
    if not excel_path.exists():
        return render_template(
            "index.html",
            result=None,
            errors=[f"Excelファイルが見つかりません: {excel_path}"],
            warnings=None,
        )

    jobs = []
    names = request.form.getlist("job_name")
    requireds = request.form.getlist("job_required")
    for name, req in zip(names, requireds):
        name = name.strip()
        if not name:
            continue
        try:
            required = int(req)
        except ValueError:
            required = 0
        jobs.append(JobConfig(name=name, required=required))

    people, time_slots = _load_people_from_excel(excel_path)
    errors = validate_inputs(jobs, time_slots)
    if errors:
        return render_template(
            "index.html", result=None, errors=errors, warnings=None
        )

    assignments, warnings = generate_shift(people, jobs, time_slots)

    if request.form.get("download") == "1":
        output = _build_excel(assignments, time_slots, people)
        return send_file(
            output,
            as_attachment=True,
            download_name="shift_output.xlsx",
            mimetype=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    return render_template(
        "index.html",
        result={"assignments": assignments, "time_slots": time_slots, "jobs": jobs},
        errors=None,
        warnings=warnings,
    )


def _build_excel(assignments, time_slots, people):
    job_by_time_person = {}
    for time_slot in time_slots:
        job_by_time_person[time_slot] = {}
        for job_name, names in assignments[time_slot].items():
            for name in names:
                job_by_time_person[time_slot][name] = job_name

    rows = []
    for person in people:
        row = {
            "名前": person.name,
            "学年": person.grade,
            "所属委員会": person.committee,
        }
        for time_slot in time_slots:
            row[time_slot] = job_by_time_person[time_slot].get(person.name, "")
        rows.append(row)

    df = pd.DataFrame(rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Shift")
    output.seek(0)
    return output


if __name__ == "__main__":
    app.run(debug=True)
