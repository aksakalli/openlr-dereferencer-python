"""Scoring functions and default weights for candidate line rating

FOW_WEIGHT + FRC_WEIGHT + GEO_WEIGHT + BEAR_WEIGHT should always be `1`.

The result of the scoring functions will be floats from 0.0 to 1.0,
with `1.0` being an exact match and 0.0 being a non-match."""

from math import degrees
from logging import debug
from openlr import FRC, FOW, LocationReferencePoint
from ..maps.wgs84 import project_along_path, distance, bearing
from .tools import coords, PointOnLine, linestring_coords

FOW_WEIGHT = 1 / 4
FRC_WEIGHT = 1 / 4
GEO_WEIGHT = 1 / 4
BEAR_WEIGHT = 1 / 4

BEAR_DIST = 20

# When comparing an LRP FOW with a candidate's FOW, this matrix defines
# how well the candidate's FOW fits as replacement for the expected value.
# The usage is `FOW_SCORING[lrp's fow][candidate's fow]`.
# It returns the score.
# The values are adopted from the openlr Java implementation.
FOW_STAND_IN_SCORE = [
    [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.5],  # Undefined FOW
    [0.50, 1.00, 0.75, 0.00, 0.00, 0.00, 0.00, 0.0],  # Motorway
    [0.50, 0.75, 1.00, 0.75, 0.50, 0.00, 0.00, 0.0],  # Multiple carriage way
    [0.50, 0.00, 0.75, 1.00, 0.50, 0.50, 0.00, 0.0],  # Single carriage way
    [0.50, 0.00, 0.50, 0.50, 1.00, 0.50, 0.00, 0.0],  # Roundabout
    [0.50, 0.00, 0.00, 0.50, 0.50, 1.00, 0.00, 0.0],  # Traffic quare
    [0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.0],  # Sliproad
    [0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.0],  # Other FOW
]


def score_fow(wanted: FOW, actual: FOW) -> float:
    "Return a score for a FOW value"
    return FOW_STAND_IN_SCORE[wanted][actual]


def score_frc(wanted: FRC, actual: FRC) -> float:
    "Return a score for a FRC value"
    return 1.0 - abs(actual - wanted) / 7


def score_geolocation(
    wanted: LocationReferencePoint, actual: PointOnLine, radius: float, is_last_lrp: bool
) -> float:
    """Scores the geolocation of a candidate.

    A distance of `radius` or more will result in a 0.0 score."""
    debug(f"Candidate coords are {actual.position()}")
    dist = distance(coords(wanted), actual.position())
    if dist < radius:
        return 1.0 - dist / radius
    return 0.0

def score_angle_difference(angle1: float, angle2: float) -> float:
    """Helper for `score_bearing` which scores the angle difference.

    Args:
        angle1, angle2: angles, in degrees.
    Returns:
        The similarity of angle1 and angle2, from 0.0 (180° difference) to 1.0 (0° difference)
    """
    difference = (abs(angle1 - angle2) + 180) % 360 - 180
    return 1 - abs(difference) / 180


def score_bearing(wanted: LocationReferencePoint, actual: PointOnLine, is_last_lrp: bool) -> float:
    """Scores the difference between expected and actual bearing angle.

    A difference of 0° will result in a 1.0 score, while 180° will cause a score of 0.0."""
    line1, line2 = actual.split()
    if is_last_lrp:
        if line1 is None:
            return 0.0
        coordinates = linestring_coords(line1)
        coordinates.reverse()
    else:
        if line2 is None:
            return 0.0
        coordinates = linestring_coords(line2)
    absolute_offset = actual.line.length * actual.relative_offset
    bearing_point = project_along_path(coordinates, absolute_offset + BEAR_DIST)
    bear = degrees(bearing(actual.position(), bearing_point))
    return score_angle_difference(wanted.bear, bear)


def score_lrp_candidate(
    wanted: LocationReferencePoint, candidate: PointOnLine, radius: float, is_last_lrp: bool
) -> float:
    """Scores the candidate (line) for the LRP.

    This is the average of fow, frc, geo and bearing score."""
    score = (
        FOW_WEIGHT * score_fow(wanted.fow, candidate.line.fow)
        + FRC_WEIGHT * score_frc(wanted.frc, candidate.line.frc)
        + GEO_WEIGHT * score_geolocation(wanted, candidate, radius, is_last_lrp)
        + BEAR_WEIGHT * score_bearing(wanted, candidate, is_last_lrp)
    )
    debug(f"scoring {candidate}")
    debug(f"geo score: {score_geolocation(wanted, candidate, radius, is_last_lrp)}")
    debug(f"fow score: {score_fow(wanted.fow, candidate.line.fow)}")
    debug(f"frc score: {score_frc(wanted.frc, candidate.line.frc)}")
    debug(f"bearing score: {score_bearing(wanted, candidate, is_last_lrp)}")
    debug(f"total score: {score}")
    return score
