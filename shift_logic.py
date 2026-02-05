from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class JobConfig:
    name: str
    required: int


@dataclass
class Person:
    name: str
    grade: int
    committee: str
    availability: Dict[str, bool]


def _would_break_consecutive(assigned_times: List[int], time_idx: int) -> bool:
    if time_idx < 2:
        return False
    return (time_idx - 1 in assigned_times) and (time_idx - 2 in assigned_times)


def generate_shift(
    people: List[Person],
    jobs: List[JobConfig],
    time_slots: List[str],
) -> Tuple[Dict[str, Dict[str, List[str]]], List[str]]:
    assignments: Dict[str, Dict[str, List[str]]] = {}
    assigned_by_time: Dict[str, set] = {t: set() for t in time_slots}
    assigned_times_by_person: Dict[str, List[int]] = {p.name: [] for p in people}
    total_assigned_count: Dict[str, int] = {p.name: 0 for p in people}
    grade_assigned_count: Dict[int, int] = {1: 0, 2: 0, 3: 0}
    warnings: List[str] = []

    people_by_name = {p.name: p for p in people}

    for time_idx, time_slot in enumerate(time_slots):
        assignments[time_slot] = {}
        for job in jobs:
            assigned: List[str] = []

            def available_candidates(filter_fn):
                for p in people:
                    if not p.availability.get(time_slot, False):
                        continue
                    if p.name in assigned_by_time[time_slot]:
                        continue
                    if _would_break_consecutive(assigned_times_by_person[p.name], time_idx):
                        continue
                    if filter_fn(p):
                        yield p

            candidates_4 = sorted(
                available_candidates(lambda p: p.grade == 4),
                key=lambda p: (total_assigned_count[p.name], p.name),
            )
            if not candidates_4:
                warnings.append(
                    f"{time_slot} / {job.name}: 4年生が確保できませんでした。"
                )
            else:
                chosen = candidates_4[0]
                assigned.append(chosen.name)

            def score_1to3(p: Person):
                return (grade_assigned_count[p.grade], total_assigned_count[p.name], p.name)

            candidates_1to3 = sorted(
                available_candidates(lambda p: 1 <= p.grade <= 3),
                key=score_1to3,
            )
            while len(assigned) < job.required and candidates_1to3:
                chosen = candidates_1to3.pop(0)
                assigned.append(chosen.name)

            if len(assigned) < job.required:
                fallback = sorted(
                    available_candidates(lambda p: True),
                    key=lambda p: (total_assigned_count[p.name], p.name),
                )
                while len(assigned) < job.required and fallback:
                    chosen = fallback.pop(0)
                    if chosen.name in assigned:
                        continue
                    assigned.append(chosen.name)
                if len(assigned) < job.required:
                    warnings.append(
                        f"{time_slot} / {job.name}: 必要人数({job.required})に満たせませんでした。"
                    )

            assignments[time_slot][job.name] = assigned

            for name in assigned:
                assigned_by_time[time_slot].add(name)
                assigned_times_by_person[name].append(time_idx)
                total_assigned_count[name] += 1
                grade = people_by_name[name].grade
                if 1 <= grade <= 3:
                    grade_assigned_count[grade] += 1

    return assignments, warnings


def validate_inputs(jobs: List[JobConfig], time_slots: List[str]) -> List[str]:
    errors: List[str] = []
    if not jobs:
        errors.append("仕事内容が1件も指定されていません。")
    for job in jobs:
        if not job.name:
            errors.append("仕事内容が空です。")
        if job.required <= 0:
            errors.append(f"{job.name or '仕事内容'}: 必要人数は1以上にしてください。")
    if not time_slots:
        errors.append("時間帯が取得できませんでした。列名に '-' を含めてください。")
    return errors
