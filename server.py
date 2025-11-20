"""
Roulette Tracker Server
Pure physics-based prediction using wheel/ball timing marks.
Version: 1.0.0
"""

from typing import List

import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =============================================================================
# CONSTANTS
# =============================================================================

ROULETTE_SEQUENCE: List[int] = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13,
    36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20,
    14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

G = 9.81
ALPHA = 0.02  # track slope angle, same as in HTML model


# =============================================================================
# DATA MODELS
# =============================================================================

class MarksRequest(BaseModel):
    wheel_times: List[float]
    ball_times: List[float]
    wheel_marks: int
    ball_marks: int
    mode: str = "3x3"


class MarksResponse(BaseModel):
    left_prediction: int
    right_prediction: int


# =============================================================================
# CORE PHYSICS HELPERS
# =============================================================================

def calculate_angular_velocity(times: List[float]) -> float:
    """Average angular frequency (rotations per second) from mark timestamps."""
    if len(times) < 2:
        return 0.0
    periods = [times[i] - times[i - 1] for i in range(1, len(times))]
    avg_period = sum(periods) / len(periods)
    return 1.0 / avg_period if avg_period > 0 else 0.0


def calculate_deceleration(times: List[float]) -> float:
    """Estimate angular deceleration using linear regression of omega(t)."""
    if len(times) < 3:
        return 0.0

    velocities: List[float] = []
    time_points: List[float] = []

    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        if dt <= 0:
            continue
        velocities.append(2 * math.pi / dt)
        time_points.append((times[i] + times[i - 1]) / 2.0)

    if len(velocities) < 2:
        return 0.0

    n = len(velocities)
    sum_x = sum(time_points)
    sum_y = sum(velocities)
    sum_xy = sum(x * v for x, v in zip(time_points, velocities))
    sum_x2 = sum(x * x for x in time_points)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    # In JS version we return -slope to get positive deceleration.
    return -slope


def predict_for_direction(wheel_times: List[float], ball_times: List[float], wheel_direction: str) -> int:
    """Port of the original JavaScript predictForDirection() to Python."""
    wheel_omega = 2 * math.pi * calculate_angular_velocity(wheel_times)
    ball_omega = 2 * math.pi * calculate_angular_velocity(ball_times)
    wheel_alpha = calculate_deceleration(wheel_times)
    ball_alpha = calculate_deceleration(ball_times)

    if wheel_alpha <= 0:
        wheel_alpha = 0.1
    if ball_alpha <= 0:
        ball_alpha = 0.1
    if wheel_omega <= 0:
        wheel_omega = 1.0
    if ball_omega <= 0:
        ball_omega = 2.0

    critical_velocity_squared = G * math.tan(ALPHA) * 0.5

    if ball_alpha > 0 and ball_omega > math.sqrt(critical_velocity_squared):
        t_drop = (ball_omega - math.sqrt(critical_velocity_squared)) / ball_alpha
    else:
        t_drop = 3.0

    if t_drop < 0:
        t_drop = 3.0
    if t_drop > 10:
        t_drop = 5.0

    theta_ball = ball_omega * t_drop - 0.5 * ball_alpha * t_drop * t_drop
    theta_wheel = wheel_omega * t_drop - 0.5 * wheel_alpha * t_drop * t_drop

    if not math.isfinite(theta_ball):
        theta_ball = 2 * math.pi * 3
    if not math.isfinite(theta_wheel):
        theta_wheel = 2 * math.pi * 2

    if wheel_direction == "left":
        relative_angle = (theta_ball + theta_wheel) / (2 * math.pi)
        direction_offset = 12
    else:
        relative_angle = (theta_ball - theta_wheel) / (2 * math.pi)
        direction_offset = 0

    pocket_offset = int(abs(relative_angle) * 37) % 37
    scatter_offset = 5
    final_pocket_index = (pocket_offset + scatter_offset + direction_offset) % 37

    return ROULETTE_SEQUENCE[final_pocket_index]


def compute_predictions(req: MarksRequest) -> MarksResponse:
    if len(req.wheel_times) < 2 or len(req.ball_times) < 2:
        raise ValueError("Not enough marks to compute prediction")

    left = predict_for_direction(req.wheel_times, req.ball_times, "left")
    right = predict_for_direction(req.wheel_times, req.ball_times, "right")
    return MarksResponse(left_prediction=left, right_prediction=right)


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Roulette Tracker Prediction Server",
    description="Physics-based prediction from wheel/ball timing marks.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/")
async def status():
    return {
        "server": "Roulette Tracker Prediction Server",
        "version": "1.0.0",
        "status": "ok",
    }


@app.post("/predict_marks", response_model=MarksResponse)
async def predict_marks(req: MarksRequest):
    try:
        return compute_predictions(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Prediction failed")
