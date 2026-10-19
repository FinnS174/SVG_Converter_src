import math
import re
import xml.etree.ElementTree as ET


# ============================================================
# IHO COLOR MAP
# ============================================================

IHO_COLOR_MAP = {
    "#768C97": "fDIAMD",
    "#cc9f80": "fUNHQD",
    "#93AEBB": "fNODTA",
    "#E38039": "fCURSR",
    "#000000": "fCHBLK",
    "#4C5B63": "fCHGRD",
    "#EA5471": "fCHRED",
    "#52E83B": "fCHGRN",
    "#E1E139": "fCHYLW",
    "#C045D1": "fCHMGD",
    "#CBA9F9": "fCHMGF",
    "#A19653": "fCHBRN",
    "#C9EDFF": "fCHWHT",
    "#BFBE8F": "fLANDA",
    "#8D642E": "fLANDF",
    "#A7D9FB": "fDEPMD",
    "#82CAFF": "fDEPMS",
    "#61B7FF": "fDEPVS",
    "#58AF9C": "fDEPIT",
    "#2F8E20": "fRADLO",
    "#2DA879": "fARPAT",
    "#2E7BFF": "fRESBL",
    "#A5A527": "fADINF",
    "#D63F24": "fPLRTE",
    "#0E1315": "fBKAJ1",
    "#1C2327": "fBKAJ2",
    "#0080FF": "fMARBL",
    "#008F84": "fMARCY",
    "#C64DA6": "fMARMG",
    "#717F77": "fMARWH",
}


# ============================================================
# TARGET S-100 COORDINATE SYSTEM
# ============================================================

TARGET_VIEWBOX_X = -4.73
TARGET_VIEWBOX_Y = -5.12
TARGET_VIEWBOX_WIDTH = 9.4
TARGET_VIEWBOX_HEIGHT = 9.61


def _calculate_geometry_transform(vb_width, vb_height):
    """
    Calculate a uniform transformation from the source SVG
    coordinate system into the target S-100 coordinate system.

    The geometry is scaled uniformly so that the entire source
    viewBox fits inside the target viewBox without distortion.

    Returns:
        scale, offset_x, offset_y
    """

    if vb_width <= 0 or vb_height <= 0:
        return 1.0, TARGET_VIEWBOX_X, TARGET_VIEWBOX_Y

    scale = min(
        TARGET_VIEWBOX_WIDTH / vb_width,
        TARGET_VIEWBOX_HEIGHT / vb_height,
    )

    scaled_width = vb_width * scale
    scaled_height = vb_height * scale

    offset_x = (
        TARGET_VIEWBOX_X
        + (TARGET_VIEWBOX_WIDTH - scaled_width) / 2.0
    )

    offset_y = (
        TARGET_VIEWBOX_Y
        + (TARGET_VIEWBOX_HEIGHT - scaled_height) / 2.0
    )

    return scale, offset_x, offset_y


def _transform_x(x, scale, offset_x):
    return offset_x + (x * scale)


def _transform_y(y, scale, offset_y):
    return offset_y + (y * scale)


def _fmt(value):
    """Format a coordinate without unnecessary trailing zeros."""

    value = float(value)

    if abs(value) < 1e-10:
        value = 0.0

    return f"{value:.2f}".rstrip("0").rstrip(".")


# ============================================================
# COLOR HELPERS
# ============================================================

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")

    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    return tuple(
        int(hex_color[i:i + 2], 16)
        for i in (0, 2, 4)
    )


def find_closest_iho_color(hex_color):
    try:
        target_rgb = hex_to_rgb(hex_color)
    except Exception:
        return None

    best_hex = None
    best_dist = float("inf")

    for iho_hex in IHO_COLOR_MAP.keys():
        r, g, b = hex_to_rgb(iho_hex)

        dist = math.sqrt(
            (r - target_rgb[0]) ** 2
            + (g - target_rgb[1]) ** 2
            + (b - target_rgb[2]) ** 2
        )

        if dist < best_dist:
            best_dist = dist
            best_hex = iho_hex

    return (
        IHO_COLOR_MAP.get(best_hex)
        if best_hex
        else None
    )


# ============================================================
# STYLE HELPERS
# ============================================================

def apply_class_styles(element, extracted_styles):
    cls_name = element.attrib.get("class")

    if not cls_name or cls_name not in extracted_styles:
        return

    style_str = extracted_styles[cls_name]

    if "class" in element.attrib:
        del element.attrib["class"]

    element.attrib["style"] = style_str


def _stroke_width_to_user_units(value, scale_factor=1.0):
    """
    Convert the source stroke width into the target coordinate system.

    Geometry is uniformly scaled by scale_factor, so stroke width
    must be scaled by the same factor to preserve the visual
    proportions of the original artwork.
    """
    if value is None:
        return None

    match = re.match(
        r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
        r"\s*([a-zA-Z]*)\s*$",
        str(value),
    )

    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower()

    if unit in ("", "user", "px"):
        return number * scale_factor

    return None


def parse_style_attribute(
    element,
    target_style,
    scale_factor=1.0,
):
    if isinstance(element, str):

        style_match = re.search(
            r'style=["\']([^"\']+)["\']',
            element,
        )

        style_attr = (
            style_match.group(1)
            if style_match
            else ""
        )

        sw_attr_match = re.search(
            r'stroke-width=["\']([^"\']+)["\']',
            element,
        )

        sw_attr = (
            sw_attr_match.group(1)
            if sw_attr_match
            else ""
        )

    else:

        style_attr = element.get("style", "")
        sw_attr = element.get("stroke-width", "")

    if style_attr:

        fill_match = re.search(
            r'fill\s*:\s*([^;]+)',
            style_attr,
            flags=re.IGNORECASE,
        )

        if fill_match:
            target_style.fill = (
                fill_match.group(1).strip()
            )

        stroke_match = re.search(
            r'stroke\s*:\s*([^;]+)',
            style_attr,
            flags=re.IGNORECASE,
        )

        if stroke_match:
            target_style.stroke = (
                stroke_match.group(1).strip()
            )

        stroke_width_match = re.search(
            r'stroke-width\s*:\s*([^;]+)',
            style_attr,
            flags=re.IGNORECASE,
        )

        if stroke_width_match:

            value = (
                stroke_width_match.group(1).strip()
            )

            converted = _stroke_width_to_user_units(
                value,
                scale_factor=scale_factor,
            )

            if converted is not None:
                target_style.strokeWidth = converted

    if sw_attr:

        converted = _stroke_width_to_user_units(
            sw_attr,
            scale_factor=scale_factor,
        )

        if converted is not None:
            target_style.strokeWidth = converted


def parse_common_attributes(
    svg_line,
    target_style,
    styles,
    enable_translation,
    scale_factor=1.0,
):
    # --------------------------------------------------------
    # Classes
    # --------------------------------------------------------

    class_match = re.search(
        r'class="([^"]+)"',
        svg_line,
    )

    if class_match:

        class_names = class_match.group(1).split()

        for class_name in class_names:

            if class_name in (
                "layout",
                "pivotPoint",
                "symbolBox",
                "svgBox",
            ):
                continue

            class_style = (
                illustratorCssClass.from_class_name(
                    class_name,
                    styles,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            )

            target_style._merge_styles(
                class_style
            )

    # --------------------------------------------------------
    # Inline style
    # --------------------------------------------------------

    parse_style_attribute(
        svg_line,
        target_style,
        scale_factor=scale_factor,
    )

    # --------------------------------------------------------
    # Explicit fill
    # --------------------------------------------------------

    fill_match = re.search(
        r'fill="([^"]+)"',
        svg_line,
    )

    if fill_match:
        target_style.fill = fill_match.group(1)

    # --------------------------------------------------------
    # Explicit stroke
    # --------------------------------------------------------

    stroke_match = re.search(
        r'stroke="([^"]+)"',
        svg_line,
    )

    if stroke_match:
        target_style.stroke = stroke_match.group(1)

    # --------------------------------------------------------
    # Explicit stroke width
    # --------------------------------------------------------

    stroke_width_match = re.search(
        r'stroke-width="([^"]+)"',
        svg_line,
    )

    if stroke_width_match:

        converted = _stroke_width_to_user_units(
            stroke_width_match.group(1),
            scale_factor=scale_factor,
        )

        if converted is not None:
            target_style.strokeWidth = converted

    # --------------------------------------------------------
    # Opacity
    # --------------------------------------------------------

    opacity_match = re.search(
        r'opacity="([^"]+)"',
        svg_line,
    )

    if opacity_match:

        try:
            target_style.opacity = float(
                opacity_match.group(1)
            )

        except ValueError:
            target_style.opacity = 1.0


def get_fill_class(color):
    """Convert an SVG fill color to an IHO S-100 fill class."""

    if not color or color.lower() in (
        "none",
        "transparent",
    ):
        return "f0"

    iho_class = find_closest_iho_color(color)

    if iho_class and iho_class.startswith("f"):
        return iho_class

    return "f0"


def get_stroke_class(color):
    """Convert an SVG stroke color to an IHO S-100 stroke class."""

    if not color or color.lower() in (
        "none",
        "transparent",
    ):
        return "sNone"

    iho_class = find_closest_iho_color(color)

    if iho_class and iho_class.startswith("f"):
        return "s" + iho_class[1:]

    return "sNone"


# ============================================================
# CSS CLASS
# ============================================================

class illustratorCssClass:

    DEFAULT_CLASS = "fDEFAULT"

    def __init__(
        self,
        enable_translation=True,
        scale_factor=1.0,
    ):
        self.fill = "none"
        self.stroke = "none"
        self.strokeWidth = None
        self.strokeMiterLimit = 4.0
        self.strokeLinecap = None
        self.strokeLinejoin = None
        self.opacity = 1.0

        self.enable_translation = enable_translation
        self.scale_factor = scale_factor

    @classmethod
    def from_class_name(
        cls,
        class_name,
        styles,
        enable_translation=True,
        scale_factor=1.0,
    ):
        instance = cls(
            enable_translation=enable_translation,
            scale_factor=scale_factor,
        )

        if styles and class_name in styles:

            style_str = styles[class_name]

            parse_style_attribute(
                f'style="{style_str}"',
                instance,
                scale_factor=scale_factor,
            )

        return instance

    def _merge_styles(self, other_style):

        if not isinstance(
            other_style,
            illustratorCssClass,
        ):
            return

        if other_style.fill is not None:
            self.fill = other_style.fill

        if other_style.stroke is not None:
            self.stroke = other_style.stroke

        if (
            hasattr(other_style, "strokeWidth")
            and other_style.strokeWidth is not None
        ):
            self.strokeWidth = (
                other_style.strokeWidth
            )

        if hasattr(
            other_style,
            "strokeMiterLimit",
        ):
            self.strokeMiterLimit = (
                other_style.strokeMiterLimit
            )

        if hasattr(
            other_style,
            "strokeLinecap",
        ):
            self.strokeLinecap = (
                other_style.strokeLinecap
            )

        if hasattr(
            other_style,
            "strokeLinejoin",
        ):
            self.strokeLinejoin = (
                other_style.strokeLinejoin
            )

        if hasattr(
            other_style,
            "opacity",
        ):
            self.opacity = other_style.opacity

    @staticmethod
    def normalize_hex_color(hex_str):

        if (
            not hex_str
            or not hex_str.startswith("#")
        ):
            return hex_str

        hex_val = hex_str[1:].strip()

        if len(hex_val) == 3:
            hex_val = "".join(
                c * 2
                for c in hex_val
            )

        return f"#{hex_val.upper()}"

    def format_attributes(self):

        classes = []
        style_parts = []
        attrs = []

        # ----------------------------------------------------
        # Fill / stroke
        # ----------------------------------------------------

        if self.enable_translation:

            fill_cls = get_fill_class(
                self.fill
            )

            stroke_cls = get_stroke_class(
                self.stroke
            )

            classes.append(fill_cls)
            classes.append(stroke_cls)

        else:

            if self.fill:
                attrs.append(
                    f'fill="{self.fill}"'
                )

            if self.stroke:
                attrs.append(
                    f'stroke="{self.stroke}"'
                )

        # ----------------------------------------------------
        # Graphic class
        # ----------------------------------------------------

        classes.insert(0, "sl")

        # ----------------------------------------------------
        # Stroke width
        # ----------------------------------------------------

        if (
            hasattr(self, "strokeWidth")
            and self.strokeWidth is not None
        ):

            try:

                width = float(
                    self.strokeWidth
                )

                if width != 0:

                    width_text = (
                        f"{width:.2f}"
                        .rstrip("0")
                        .rstrip(".")
                    )

                    style_parts.append(
                        f"stroke-width:{width_text};"
                    )

            except (
                ValueError,
                TypeError,
            ):
                pass

        # ----------------------------------------------------
        # Other stroke attributes
        # ----------------------------------------------------

        if (
            hasattr(
                self,
                "strokeMiterLimit",
            )
            and float(
                self.strokeMiterLimit
            ) != 4.0
        ):

            style_parts.append(
                f"stroke-miterlimit:"
                f"{self.strokeMiterLimit};"
            )

        if (
            hasattr(
                self,
                "strokeLinecap",
            )
            and self.strokeLinecap
        ):

            style_parts.append(
                f"stroke-linecap:"
                f"{self.strokeLinecap};"
            )

        if (
            hasattr(
                self,
                "strokeLinejoin",
            )
            and self.strokeLinejoin
        ):

            style_parts.append(
                f"stroke-linejoin:"
                f"{self.strokeLinejoin};"
            )

        # ----------------------------------------------------
        # Class attribute
        # ----------------------------------------------------

        if classes:

            attrs.append(
                f'class="{" ".join(classes)}"'
            )

        # ----------------------------------------------------
        # Style attribute
        # ----------------------------------------------------

        if style_parts:

            attrs.append(
                f'style="{"".join(style_parts)}"'
            )

        return " ".join(attrs)


# ============================================================
# RECTANGLE
# ============================================================

class illustratorRect:

    def __init__(
        self,
        svg_line,
        styles,
        vb_width,
        vb_height,
        enable_translation=True,
        scale_factor=1.0,
    ):

        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0

        self.style = illustratorCssClass(
            enable_translation,
            scale_factor=scale_factor,
        )

        self.transformation = -1

        parse_style_attribute(
            svg_line,
            self.style,
            scale_factor=scale_factor,
        )

        parse_common_attributes(
            svg_line,
            self.style,
            styles,
            enable_translation,
            scale_factor=scale_factor,
        )

        fields = re.findall(
            r'(\S+)="([^"]+)"',
            svg_line,
        )

        for attr_name, attr_value in fields:

            if attr_name == "x":
                self.x = float(attr_value)

            elif attr_name == "y":
                self.y = float(attr_value)

            elif attr_name == "width":
                self.width = float(attr_value)

            elif attr_name == "height":
                self.height = float(attr_value)

            elif attr_name == "transform":

                self.transformation = list(
                    map(
                        float,
                        re.findall(
                            r"[-+]?\d*\.?\d+",
                            attr_value,
                        ),
                    )
                )

        # ----------------------------------------------------
        # Bake geometry scaling directly into rectangle
        # ----------------------------------------------------

        scale, ox, oy = _calculate_geometry_transform(
            vb_width,
            vb_height,
        )

        self.x = _transform_x(
            self.x,
            scale,
            ox,
        )

        self.y = _transform_y(
            self.y,
            scale,
            oy,
        )

        self.width *= scale
        self.height *= scale

    def hasTransformation(self):
        return self.transformation != -1

    def __str__(self):

        attrs = self.style.format_attributes()

        return (
            f'<rect '
            f'x="{_fmt(self.x)}" '
            f'y="{_fmt(self.y)}" '
            f'width="{_fmt(self.width)}" '
            f'height="{_fmt(self.height)}" '
            f"{attrs} />"
        )


# ============================================================
# ELLIPSE
# ============================================================

class illustratorEllipse:

    def __init__(
        self,
        svg_line,
        styles,
        vb_width,
        vb_height,
        enable_translation=True,
        scale_factor=1.0,
    ):

        self.cx = 0
        self.cy = 0
        self.rx = 0
        self.ry = 0

        self.style = illustratorCssClass(
            enable_translation,
            scale_factor=scale_factor,
        )

        parse_style_attribute(
            svg_line,
            self.style,
            scale_factor=scale_factor,
        )

        parse_common_attributes(
            svg_line,
            self.style,
            styles,
            enable_translation,
            scale_factor=scale_factor,
        )

        attributes = dict(
            re.findall(
                r'(\w+)="([^"]+)"',
                svg_line,
            )
        )

        if "cx" in attributes:
            self.cx = float(
                attributes["cx"]
            )

        if "cy" in attributes:
            self.cy = float(
                attributes["cy"]
            )

        if "rx" in attributes:
            self.rx = float(
                attributes["rx"]
            )

        if "ry" in attributes:
            self.ry = float(
                attributes["ry"]
            )

        # ----------------------------------------------------
        # Bake geometry scaling
        # ----------------------------------------------------

        scale, ox, oy = _calculate_geometry_transform(
            vb_width,
            vb_height,
        )

        self.cx = _transform_x(
            self.cx,
            scale,
            ox,
        )

        self.cy = _transform_y(
            self.cy,
            scale,
            oy,
        )

        self.rx *= scale
        self.ry *= scale

    def __str__(self):

        attrs = self.style.format_attributes()

        start_x = self.cx - self.rx
        start_y = self.cy

        arc_x = self.rx * 2

        return (
            f'<path '
            f'd="M {_fmt(start_x)},{_fmt(start_y)} '
            f'a {_fmt(self.rx)},{_fmt(self.ry)} '
            f'0 1,0 {_fmt(arc_x)},0 '
            f'a {_fmt(self.rx)},{_fmt(self.ry)} '
            f'0 1,0 {_fmt(-arc_x)},0 Z" '
            f"{attrs} />"
        )


# ============================================================
# CIRCLE
# ============================================================

class illustratorCircle:

    def __init__(
        self,
        svg_line,
        styles,
        vb_width,
        vb_height,
        enable_translation=True,
        scale_factor=1.0,
    ):

        self.cx = 0
        self.cy = 0
        self.r = 0

        self.style = illustratorCssClass(
            enable_translation,
            scale_factor=scale_factor,
        )

        parse_style_attribute(
            svg_line,
            self.style,
            scale_factor=scale_factor,
        )

        parse_common_attributes(
            svg_line,
            self.style,
            styles,
            enable_translation,
            scale_factor=scale_factor,
        )

        attributes = dict(
            re.findall(
                r'(\w+)="([^"]+)"',
                svg_line,
            )
        )

        if "cx" in attributes:
            self.cx = float(
                attributes["cx"]
            )

        if "cy" in attributes:
            self.cy = float(
                attributes["cy"]
            )

        if "r" in attributes:
            self.r = float(
                attributes["r"]
            )

        # ----------------------------------------------------
        # Bake geometry scaling
        # ----------------------------------------------------

        scale, ox, oy = _calculate_geometry_transform(
            vb_width,
            vb_height,
        )

        self.cx = _transform_x(
            self.cx,
            scale,
            ox,
        )

        self.cy = _transform_y(
            self.cy,
            scale,
            oy,
        )

        self.r *= scale

    def __str__(self):

        attrs = self.style.format_attributes()

        return (
            f'<circle '
            f'cx="{_fmt(self.cx)}" '
            f'cy="{_fmt(self.cy)}" '
            f'r="{_fmt(self.r)}" '
            f"{attrs} />"
        )


# ============================================================
# LINE
# ============================================================

class illustratorLine:

    def __init__(
        self,
        svg_line,
        styles,
        vb_width,
        vb_height,
        enable_translation=True,
        scale_factor=1.0,
    ):

        self.x1 = 0
        self.y1 = 0
        self.x2 = 0
        self.y2 = 0

        self.style = illustratorCssClass(
            enable_translation,
            scale_factor=scale_factor,
        )

        parse_style_attribute(
            svg_line,
            self.style,
            scale_factor=scale_factor,
        )

        parse_common_attributes(
            svg_line,
            self.style,
            styles,
            enable_translation,
            scale_factor=scale_factor,
        )

        attributes = dict(
            re.findall(
                r'(\w+)="([^"]+)"',
                svg_line,
            )
        )

        if "x1" in attributes:
            self.x1 = float(attributes["x1"])

        if "y1" in attributes:
            self.y1 = float(attributes["y1"])

        if "x2" in attributes:
            self.x2 = float(attributes["x2"])

        if "y2" in attributes:
            self.y2 = float(attributes["y2"])

        # ----------------------------------------------------
        # Bake geometry scaling
        # ----------------------------------------------------

        scale, ox, oy = _calculate_geometry_transform(
            vb_width,
            vb_height,
        )

        self.x1 = _transform_x(
            self.x1,
            scale,
            ox,
        )

        self.y1 = _transform_y(
            self.y1,
            scale,
            oy,
        )

        self.x2 = _transform_x(
            self.x2,
            scale,
            ox,
        )

        self.y2 = _transform_y(
            self.y2,
            scale,
            oy,
        )

    def __str__(self):

        attrs = self.style.format_attributes()

        return (
            f'<line '
            f'x1="{_fmt(self.x1)}" '
            f'y1="{_fmt(self.y1)}" '
            f'x2="{_fmt(self.x2)}" '
            f'y2="{_fmt(self.y2)}" '
            f"{attrs} />"
        )


# ============================================================
# SVG PATH
# ============================================================

class illustratorPath:

    def __init__(
        self,
        svg_line=None,
        styles=None,
        vb_width=0,
        vb_height=0,
        enable_translation=True,
        scale_factor=1.0,
    ):

        self.points = []
        self.vb_width = vb_width
        self.vb_height = vb_height
        self.original_path_data = ""

        self.style = illustratorCssClass(
            enable_translation,
            scale_factor=scale_factor,
        )

        if svg_line:

            parse_style_attribute(
                svg_line,
                self.style,
                scale_factor=scale_factor,
            )

            parse_common_attributes(
                svg_line,
                self.style,
                styles,
                enable_translation,
                scale_factor=scale_factor,
            )

            d_match = re.search(
                r'd="([^"]+)"',
                svg_line,
            )

            if d_match:

                self.original_path_data = (
                    d_match.group(1)
                )

                self.points = (
                    self._parse_path_commands(
                        self.original_path_data
                    )
                )

    # --------------------------------------------------------
    # Parse SVG commands
    # --------------------------------------------------------

    def _parse_path_commands(self, path_data):

        token_pattern = (
            r'[AaCcHhLlMmQqSsTtVvZz]'
            r'|[-+]?(?:'
            r'\d+(?:\.\d*)?'
            r'|\.\d+'
            r')(?:[eE][-+]?\d+)?'
        )

        tokens = re.findall(
            token_pattern,
            path_data,
        )

        commands = []

        current_command = None
        values = []

        parameter_counts = {
            "M": 2,
            "L": 2,
            "H": 1,
            "V": 1,
            "C": 6,
            "S": 4,
            "Q": 4,
            "T": 2,
            "A": 7,
        }

        i = 0

        while i < len(tokens):

            token = tokens[i]

            if re.fullmatch(
                r'[AaCcHhLlMmQqSsTtVvZz]',
                token,
            ):

                current_command = token
                i += 1

                if current_command.upper() == "Z":
                    commands.append(
                        ("Z", True, [])
                    )
                    continue

            if current_command is None:
                i += 1
                continue

            upper = current_command.upper()

            if upper not in parameter_counts:
                continue

            count = parameter_counts[upper]

            while (
                i < len(tokens)
                and not re.fullmatch(
                    r'[AaCcHhLlMmQqSsTtVvZz]',
                    tokens[i],
                )
            ):

                if i + count > len(tokens):
                    break

                chunk = tokens[
                    i:i + count
                ]

                if any(
                    re.fullmatch(
                        r'[AaCcHhLlMmQqSsTtVvZz]',
                        x,
                    )
                    for x in chunk
                ):
                    break

                commands.append(
                    (
                        current_command,
                        False,
                        [
                            float(x)
                            for x in chunk
                        ],
                    )
                )

                i += count

                # After M, additional coordinate pairs
                # are implicit L commands.
                if (
                    current_command == "M"
                    and count == 2
                ):
                    current_command = "L"

                elif (
                    current_command == "m"
                    and count == 2
                ):
                    current_command = "l"

            # Continue to next explicit command.

        return commands

    # --------------------------------------------------------
    # Transform path commands
    # --------------------------------------------------------

    def _transform_commands(self):

        scale, ox, oy = (
            _calculate_geometry_transform(
                self.vb_width,
                self.vb_height,
            )
        )

        output = []

        current_x = 0.0
        current_y = 0.0

        start_x = 0.0
        start_y = 0.0

        for command, is_close, values in self.points:

            if is_close or command.upper() == "Z":

                output.append("Z")

                current_x = start_x
                current_y = start_y

                continue

            upper = command.upper()
            relative = command.islower()

            v = list(values)

            # ------------------------------------------------
            # MOVETO
            # ------------------------------------------------

            if upper == "M":

                x, y = v

                if relative:
                    x = current_x + x
                    y = current_y + y

                tx = _transform_x(
                    x,
                    scale,
                    ox,
                )

                ty = _transform_y(
                    y,
                    scale,
                    oy,
                )

                output.append(
                    f"M {_fmt(tx)},{_fmt(ty)}"
                )

                current_x = x
                current_y = y

                start_x = x
                start_y = y

            # ------------------------------------------------
            # LINETO
            # ------------------------------------------------

            elif upper == "L":

                x, y = v

                if relative:
                    x = current_x + x
                    y = current_y + y

                output.append(
                    f"L {_fmt(_transform_x(x, scale, ox))},"
                    f"{_fmt(_transform_y(y, scale, oy))}"
                )

                current_x = x
                current_y = y

            # ------------------------------------------------
            # HORIZONTAL
            # ------------------------------------------------

            elif upper == "H":

                x = v[0]

                if relative:
                    x = current_x + x

                output.append(
                    f"H {_fmt(_transform_x(x, scale, ox))}"
                )

                current_x = x

            # ------------------------------------------------
            # VERTICAL
            # ------------------------------------------------

            elif upper == "V":

                y = v[0]

                if relative:
                    y = current_y + y

                output.append(
                    f"V {_fmt(_transform_y(y, scale, oy))}"
                )

                current_y = y

            # ------------------------------------------------
            # CUBIC BEZIER
            # ------------------------------------------------

            elif upper == "C":

                x1, y1, x2, y2, x, y = v

                if relative:
                    x1 += current_x
                    y1 += current_y
                    x2 += current_x
                    y2 += current_y
                    x += current_x
                    y += current_y

                output.append(
                    "C "
                    f"{_fmt(_transform_x(x1, scale, ox))},"
                    f"{_fmt(_transform_y(y1, scale, oy))} "
                    f"{_fmt(_transform_x(x2, scale, ox))},"
                    f"{_fmt(_transform_y(y2, scale, oy))} "
                    f"{_fmt(_transform_x(x, scale, ox))},"
                    f"{_fmt(_transform_y(y, scale, oy))}"
                )

                current_x = x
                current_y = y

            # ------------------------------------------------
            # SMOOTH CUBIC
            # ------------------------------------------------

            elif upper == "S":

                x2, y2, x, y = v

                if relative:
                    x2 += current_x
                    y2 += current_y
                    x += current_x
                    y += current_y

                output.append(
                    "S "
                    f"{_fmt(_transform_x(x2, scale, ox))},"
                    f"{_fmt(_transform_y(y2, scale, oy))} "
                    f"{_fmt(_transform_x(x, scale, ox))},"
                    f"{_fmt(_transform_y(y, scale, oy))}"
                )

                current_x = x
                current_y = y

            # ------------------------------------------------
            # QUADRATIC BEZIER
            # ------------------------------------------------

            elif upper == "Q":

                x1, y1, x, y = v

                if relative:
                    x1 += current_x
                    y1 += current_y
                    x += current_x
                    y += current_y

                output.append(
                    "Q "
                    f"{_fmt(_transform_x(x1, scale, ox))},"
                    f"{_fmt(_transform_y(y1, scale, oy))} "
                    f"{_fmt(_transform_x(x, scale, ox))},"
                    f"{_fmt(_transform_y(y, scale, oy))}"
                )

                current_x = x
                current_y = y

            # ------------------------------------------------
            # SMOOTH QUADRATIC
            # ------------------------------------------------

            elif upper == "T":

                x, y = v

                if relative:
                    x += current_x
                    y += current_y

                output.append(
                    f"T {_fmt(_transform_x(x, scale, ox))},"
                    f"{_fmt(_transform_y(y, scale, oy))}"
                )

                current_x = x
                current_y = y

            # ------------------------------------------------
            # ARC
            # ------------------------------------------------

            elif upper == "A":

                rx, ry, rotation, large_arc, sweep, x, y = v

                if relative:
                    x += current_x
                    y += current_y

                rx *= scale
                ry *= scale

                output.append(
                    "A "
                    f"{_fmt(rx)},{_fmt(ry)} "
                    f"{_fmt(rotation)} "
                    f"{int(large_arc)} "
                    f"{int(sweep)} "
                    f"{_fmt(_transform_x(x, scale, ox))},"
                    f"{_fmt(_transform_y(y, scale, oy))}"
                )

                current_x = x
                current_y = y

        return " ".join(output)

    def __str__(self):

        path_data = self._transform_commands()

        attrs = self.style.format_attributes()

        return (
            f'<path '
            f'd="{path_data}" '
            f"{attrs} />"
        )


# ============================================================
# POLYGON
# ============================================================

class illustratorPolygon:

    def __init__(
        self,
        svg_line,
        styles,
        vb_width,
        vb_height,
        enable_translation=True,
        scale_factor=1.0,
    ):

        self.points = []

        self.vbWidth = vb_width
        self.vbHeight = vb_height

        self.original_fill = None

        self.style = illustratorCssClass(
            enable_translation,
            scale_factor=scale_factor,
        )

        parse_style_attribute(
            svg_line,
            self.style,
            scale_factor=scale_factor,
        )

        parse_common_attributes(
            svg_line,
            self.style,
            styles,
            enable_translation,
            scale_factor=scale_factor,
        )

        points_match = re.search(
            r'points="([^"]+)"',
            svg_line,
        )

        if points_match:

            raw = (
                points_match
                .group(1)
                .replace(",", " ")
                .strip()
                .split()
            )

            raw_floats = list(
                map(float, raw)
            )

            source_points = [
                (
                    raw_floats[i],
                    raw_floats[i + 1],
                )
                for i in range(
                    0,
                    len(raw_floats),
                    2,
                )
                if i + 1 < len(raw_floats)
            ]

            if (
                len(source_points) > 2
                and source_points[0]
                == source_points[-1]
            ):
                source_points.pop()

            # ------------------------------------------------
            # Bake geometry scaling
            # ------------------------------------------------

            scale, ox, oy = (
                _calculate_geometry_transform(
                    vb_width,
                    vb_height,
                )
            )

            self.points = [
                (
                    _transform_x(
                        x,
                        scale,
                        ox,
                    ),
                    _transform_y(
                        y,
                        scale,
                        oy,
                    ),
                )
                for x, y in source_points
            ]

    def __str__(self):

        formatted = [
            f"{_fmt(x)},{_fmt(y)}"
            for x, y in self.points
        ]

        attrs = self.style.format_attributes()

        return (
            f'<polygon '
            f'points="{" ".join(formatted)}" '
            f"{attrs} />"
        )