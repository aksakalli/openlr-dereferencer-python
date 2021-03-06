"Decoding logic for point (along line, ...) locations"

from typing import NamedTuple, Tuple, Optional
from openlr import (
    Coordinates,
    PointAlongLineLocation,
    Orientation,
    SideOfRoad,
    PoiWithAccessPointLocation,
)
from ..maps import MapReader, path_length
from ..maps.abstract import Line
from ..observer import DecoderObserver
from ..maps.wgs84 import project_along_path
from .line_decoding import dereference_path
from .line_location import get_lines, Route, combine_routes
from . import LRDecodeError


class PointAlongLine(NamedTuple):
    """A dereferenced point along line location.

    Contains the coordinates as well as the road on which it was located."""

    line: Line
    positive_offset: float
    side: SideOfRoad
    orientation: Orientation

    def coordinates(self) -> Coordinates:
        "Returns the actual geo coordinate"
        return project_along_path(list(self.line.coordinates()), self.positive_offset)


def point_along_linelocation(route: Route, length: float) -> Tuple[Line, float]:
    """Steps `length` meters into the `route` and returns the Line + offset of the point in meters.

    If the path is exhausted (`length` longer than `route`), raises an LRDecodeError."""
    leftover_length = length
    leftover_length -= route.start.line.length * (1.0 - route.start.relative_offset)
    if leftover_length < 0.0:
        return route.start.line, route.start.line.length * route.start.relative_offset + length
    for road in route.path_inbetween:
        if leftover_length > road.length:
            leftover_length -= road.length
        else:
            return road, leftover_length
    end_offset = route.end.line.length * route.end.relative_offset
    leftover_length -= end_offset
    if leftover_length < 0.0:
        return route.end.line, end_offset
    raise LRDecodeError("Path length exceeded while projecting point")


def decode_pointalongline(
    reference: PointAlongLineLocation, reader: MapReader, radius: float, observer: Optional[DecoderObserver]
) -> PointAlongLine:
    "Decodes a point along line location reference"
    path = combine_routes(dereference_path(reference.points, reader, radius, observer))
    absolute_offset = path.length() * reference.poffs
    line_object, line_offset = point_along_linelocation(path, absolute_offset)
    return PointAlongLine(line_object, line_offset, reference.sideOfRoad, reference.orientation)


class PoiWithAccessPoint(NamedTuple):
    "A dereferenced POI with access point location."
    line: Line
    positive_offset: float
    side: SideOfRoad
    orientation: Orientation
    poi: Coordinates

    def access_point_coordinates(self) -> Coordinates:
        "Returns the geo coordinates of the access point"
        return project_along_path(list(self.line.coordinates()), self.positive_offset)


def decode_poi_with_accesspoint(
    reference: PoiWithAccessPointLocation, reader: MapReader, radius: float, observer: Optional[DecoderObserver]
    ) -> PoiWithAccessPoint:
    "Decodes a point along line location reference into a Coordinates tuple"
    path = combine_routes(dereference_path(reference.points, reader, radius, observer))
    absolute_offset = path_length(get_lines([path])) * reference.poffs
    line, line_offset = point_along_linelocation(path, absolute_offset)
    return PoiWithAccessPoint(
        line,
        line_offset,
        reference.sideOfRoad,
        reference.orientation,
        Coordinates(reference.lon, reference.lat),
    )
