import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

from classDefs import (
    illustratorRect,
    illustratorCircle,
    illustratorEllipse,
    illustratorLine,
    illustratorPath,
    illustratorPolygon,
)

from stringConstants import (
    XML_VERSION,
    PIVOT_POINT,
    buildTitle,
    buildDescription,
    buildMetadata,
    TITLE,
    DESCRIPTION,
)

# S-100 / Symbol Builder coordinate system
TARGET_VIEWBOX_X = -4.73
TARGET_VIEWBOX_Y = -5.12
TARGET_VIEWBOX_WIDTH = 9.4
TARGET_VIEWBOX_HEIGHT = 9.61

items = []
styles = {}

viewBoxX = 0.0
viewBoxY = 0.0
viewBoxWidth = 0.0
viewBoxHeight = 0.0
outputWidthMM = 0.0
outputHeightMM = 0.0
geometry_scale = 1.0
geometry_offset_x = 0.0
geometry_offset_y = 0.0

title = TITLE
description = DESCRIPTION

filePointer = None
folder = None

OUTPUT_STYLE_SHEET = '<?xml-stylesheet href="SVGStyle.css" type="text/css"?>\n'

def extract_styles(svg_content):
    """Extract CSS class rules from source SVG style blocks."""

    extracted = {}

    # Find every <style>...</style> block
    style_blocks = re.findall(
        r"<style\b[^>]*>(.*?)</style>",
        svg_content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for block in style_blocks:

        # Remove CSS comments
        block = re.sub(
            r"/\*.*?\*/",
            "",
            block,
            flags=re.DOTALL,
        )

        # Find .class { ... } rules
        rules = re.findall(
            r"([^{}]+)\{([^{}]*)\}",
            block,
            flags=re.DOTALL,
        )

        for selectors, declarations in rules:

            declarations = re.sub(
                r"\s+",
                " ",
                declarations,
            ).strip()

            for selector in selectors.split(","):

                selector = selector.strip()

                # We only want CSS classes
                if not selector.startswith("."):
                    continue

                class_name = selector[1:].strip()

                if not class_name:
                    continue

                extracted[class_name] = declarations

    return extracted

def _svg_attr(svg_tag, name, default=None):
    match = re.search(
        rf'\b{re.escape(name)}\s*=\s*"([^"]+)"',
        svg_tag,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else default


def _parse_viewbox(svg_tag):
    """Return source viewBox as min-x, min-y, width, height."""
    raw = _svg_attr(svg_tag, "viewBox")

    if raw:
        values = re.split(r"[\s,]+", raw.strip())
        if len(values) == 4:
            try:
                values = tuple(float(v) for v in values)
                if values[2] > 0 and values[3] > 0:
                    return values
            except ValueError:
                pass

    def numeric_length(value):
        if value is None:
            return None

        match = re.match(
            r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
            value,
        )
        return float(match.group(1)) if match else None

    width = numeric_length(_svg_attr(svg_tag, "width"))
    height = numeric_length(_svg_attr(svg_tag, "height"))

    if width and height:
        return 0.0, 0.0, width, height

    raise ValueError(
        "Source SVG has no valid viewBox and no usable width/height."
    )


def _length_to_mm(value):
    """Convert a simple SVG physical length to millimetres."""
    if value is None:
        return None

    match = re.match(
        r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*([a-zA-Z%]*)\s*$",
        value,
    )

    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower()

    if unit in ("", "mm"):
        return number
    if unit == "cm":
        return number * 10.0
    if unit == "in":
        return number * 25.4
    if unit == "pt":
        return number * 25.4 / 72.0
    if unit == "pc":
        return number * 25.4 / 6.0
    if unit == "px":
        return number * 25.4 / 96.0

    return None


def _get_physical_size_mm(svg_tag, vb_width, vb_height):
    width = _length_to_mm(_svg_attr(svg_tag, "width"))
    height = _length_to_mm(_svg_attr(svg_tag, "height"))

    if width is None:
        width = vb_width
    if height is None:
        height = vb_height

    if width <= 0 or height <= 0:
        raise ValueError("SVG physical dimensions must be positive.")

    return width, height


def _format_number(value):
    value = float(value)
    if abs(value) < 1e-9:
        value = 0.0
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _remove_source_layout_items():
    global items
    filtered = []

    for item in items:
        text = str(item)
        match = re.search(
            r'class="([^"]+)"',
            text,
        )

        if match:
            classes = match.group(1).split()
            if any(
                cls in ("layout", "pivotPoint", "symbolBox", "svgBox")
                for cls in classes
            ):
                continue

        filtered.append(item)

    items = filtered


def convert_svg(sFolder, sFile, dFolder, dFile, enable_translation):
    global items, styles, filePointer, folder
    global title, description
    global viewBoxX, viewBoxY, viewBoxWidth, viewBoxHeight
    global outputWidthMM, outputHeightMM
    global geometry_scale, geometry_offset_x, geometry_offset_y

    try:
        items.clear()

        if filePointer is None:
            messagebox.showerror("Error", "Please select an SVG file first.")
            return

        filePointer.seek(0)
        content = filePointer.read()

        if not content.strip():
            raise ValueError("The selected SVG file is empty.")

        styles = extract_styles(content)

        print("\n=== EXTRACTED STYLES ===")
        for name, rule in styles.items():
            print(f"{name!r} -> {rule!r}")
        print("========================\n")
        
        enable_translation = bool(enable_translation.get())

        svg_match = re.search(
            r"<svg\b[^>]*>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not svg_match:
            raise ValueError("No SVG root element was found.")

        svg_tag = svg_match.group(0)

        (
            viewBoxX,
            viewBoxY,
            viewBoxWidth,
            viewBoxHeight,
        ) = _parse_viewbox(svg_tag)


        '''
        outputWidthMM, outputHeightMM = _get_physical_size_mm(
            svg_tag,
            viewBoxWidth,
            viewBoxHeight,
        )
        '''

        outputWidthMM = 9.4
        outputHeightMM = 9.61

        # Target S-100 coordinate system
        TARGET_VIEWBOX_X = -4.73
        TARGET_VIEWBOX_Y = -5.12
        TARGET_VIEWBOX_WIDTH = 9.4
        TARGET_VIEWBOX_HEIGHT = 9.61

        # Scale the source artwork uniformly so it fits the target viewBox.
        geometry_scale = min(
            TARGET_VIEWBOX_WIDTH / viewBoxWidth,
            TARGET_VIEWBOX_HEIGHT / viewBoxHeight,
        )

        scaled_width = viewBoxWidth * geometry_scale
        scaled_height = viewBoxHeight * geometry_scale

        # Center the source artwork inside the target viewBox.
        geometry_offset_x = (
            TARGET_VIEWBOX_X
            + (TARGET_VIEWBOX_WIDTH - scaled_width) / 2
        )

        geometry_offset_y = (
            TARGET_VIEWBOX_Y
            + (TARGET_VIEWBOX_HEIGHT - scaled_height) / 2
        )

        # Do NOT use this to scale stroke widths.
        scale_factor = geometry_scale
        
        shape_tags = re.findall(
            r"<(rect|circle|ellipse|line|path|polygon)\b([^>]*)>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for tag, attrs in shape_tags:
            tag = tag.lower()
            element = f"<{tag}{attrs}>"

            # The classDefs constructors require the source viewBox width and
            # height.  Pass those values to every illustrator* class.
            if tag == "rect":
                item = illustratorRect(
                    element,
                    styles,
                    viewBoxWidth,
                    viewBoxHeight,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            elif tag == "circle":
                item = illustratorCircle(
                    element,
                    styles,
                    viewBoxWidth,
                    viewBoxHeight,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            elif tag == "ellipse":
                item = illustratorEllipse(
                    element,
                    styles,
                    viewBoxWidth,
                    viewBoxHeight,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            elif tag == "line":
                item = illustratorLine(
                    element,
                    styles,
                    viewBoxWidth,
                    viewBoxHeight,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            elif tag == "path":
                item = illustratorPath(
                    element,
                    styles,
                    viewBoxWidth,
                    viewBoxHeight,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            elif tag == "polygon":
                item = illustratorPolygon(
                    element,
                    styles,
                    viewBoxWidth,
                    viewBoxHeight,
                    enable_translation,
                    scale_factor=scale_factor,
                )
            else:
                continue

            items.append(item)

        _remove_source_layout_items()

        title_match = re.search(
            r"<title\b[^>]*>(.*?)</title>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        desc_match = re.search(
            r"<desc\b[^>]*>(.*?)</desc>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        title = (
            title_match.group(1).strip()
            if title_match
            else TITLE
        )

        description = (
            desc_match.group(1).strip()
            if desc_match
            else DESCRIPTION
        )

        dest_dir = dFolder.get("1.0", "end").strip()

        target_folder = (
            folder
            if "optional" in dest_dir.lower() or not dest_dir
            else dest_dir
        )

        if not target_folder:
            raise ValueError("No destination folder is available.")

        os.makedirs(target_folder, exist_ok=True)

        destination_name = dFile.get("1.0", "end").strip()

        if not destination_name:
            raise ValueError("Please provide a destination file name.")

        if not destination_name.lower().endswith(".svg"):
            destination_name += ".svg"

        new_filename = os.path.join(
            target_folder,
            destination_name,
        )

        write_output_svg(
            new_filename,
            enable_translation,
            target_folder,
        )

        messagebox.showinfo(
            "Success",
            "SVG Converted Successfully!",
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        messagebox.showerror(
            "Error",
            f"Conversion failed:\n\n{type(e).__name__}: {e}",
        )


def write_output_svg(fp, enable_translation, target_folder):
    if enable_translation:
        css_source = os.path.join(folder, "SVGStyle.css")
        css_destination = os.path.join(target_folder, "SVGStyle.css")

        if os.path.exists(css_source):
            # Don't copy the stylesheet if source and destination
            # are already the same file.
            if os.path.abspath(css_source) != os.path.abspath(css_destination):
                shutil.copy2(css_source, css_destination)

    with open(fp, "w", encoding="utf-8") as f:
        # XML declaration
        f.write(XML_VERSION + "\n")

        # Stylesheet
        f.write(OUTPUT_STYLE_SHEET)

        # Root SVG
        f.write(
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'version="1.2" '
            'baseProfile="tiny" '
            'xml:space="preserve" '
            'style="shape-rendering:geometricPrecision; fill-rule:evenodd;" '
            f'width="{_format_number(TARGET_VIEWBOX_WIDTH)}mm" '
            f'height="{_format_number(TARGET_VIEWBOX_HEIGHT)}mm" '
            f'viewBox="{_format_number(TARGET_VIEWBOX_X)} '
            f'{_format_number(TARGET_VIEWBOX_Y)} '
            f'{_format_number(TARGET_VIEWBOX_WIDTH)} '
            f'{_format_number(TARGET_VIEWBOX_HEIGHT)}">\n'
        )

        # Title
        f.write(f"  {buildTitle(title)}\n")

        # Description
        f.write(f"  {buildDescription(description)}\n")

        # Metadata
        f.write(f"  {buildMetadata()}\n")

        # Pivot point
        f.write(
            '  <circle class="pivotPoint layout" '
            'fill="none" '
            'cx="0.00" '
            'cy="0.00" '
            'r="0.4" />\n'
        )

        # Target symbol box
        f.write(
            '  <rect class="symbolBox layout" '
            'fill="none" '
            f'x="{_format_number(TARGET_VIEWBOX_X)}" '
            f'y="{_format_number(TARGET_VIEWBOX_Y)}" '
            f'width="{_format_number(TARGET_VIEWBOX_WIDTH)}" '
            f'height="{_format_number(TARGET_VIEWBOX_HEIGHT)}" />\n'
        )

        # Target SVG box
        f.write(
            '  <rect class="svgBox layout" '
            'fill="none" '
            f'x="{_format_number(TARGET_VIEWBOX_X)}" '
            f'y="{_format_number(TARGET_VIEWBOX_Y)}" '
            f'width="{_format_number(TARGET_VIEWBOX_WIDTH)}" '
            f'height="{_format_number(TARGET_VIEWBOX_HEIGHT)}" />\n'
        )

        # ---------------------------------------------------------
        # Scale ALL converted geometry as one group.
        #
        # The individual elements remain in their original
        # source coordinate system. The group transform maps
        # that coordinate system into the target S-100 viewBox.
        # ---------------------------------------------------------

        '''
        f.write(
            '  <g transform="matrix('
            f'{_format_number(geometry_scale)} 0 0 '
            f'{_format_number(geometry_scale)} '
            f'{_format_number(geometry_offset_x)} '
            f'{_format_number(geometry_offset_y)})">\n'
        )
        '''

        for item in items:
            f.write(f"    {str(item)}\n")

        # f.write("  </g>\n")

        # Close SVG
        f.write("</svg>\n")


def select_file(sFolder, sFile, dFile):
    global filePointer, folder

    filename = filedialog.askopenfilename(
        title="Select SVG File",
        filetypes=[
            ("SVG files", "*.svg"),
            ("All files", "*.*"),
        ],
    )

    if not filename:
        return

    if filePointer is not None:
        try:
            filePointer.close()
        except Exception:
            pass

    filePointer = open(
        filename,
        "r",
        encoding="utf-8-sig",
    )

    folder = os.path.dirname(filename)

    sFolder.config(state="normal")
    sFile.config(state="normal")

    sFolder.delete("1.0", "end")
    sFile.delete("1.0", "end")
    dFile.delete("1.0", "end")

    sFolder.insert("end", folder)
    sFile.insert("end", os.path.basename(filename))
    dFile.insert(
        "1.0",
        "converted_" + os.path.basename(filename),
    )

    sFolder.config(state="disabled")
    sFile.config(state="disabled")


def select_dest_folder(dFolder):
    selected = filedialog.askdirectory()

    if selected:
        dFolder.delete("1.0", "end")
        dFolder.insert("1.0", selected)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x400")
    root.title("S-100 SVG Converter")

    enable_translation = tk.BooleanVar(value=True)

    tk.Label(root, text="Source Folder").place(x=10, y=10)

    txtSourceFolder = tk.Text(root, height=1, width=85)
    txtSourceFolder.config(state="disabled")
    txtSourceFolder.place(x=160, y=10)

    tk.Label(root, text="Source File").place(x=10, y=40)

    txtSourceFile = tk.Text(root, height=1, width=85)
    txtSourceFile.config(state="disabled")
    txtSourceFile.place(x=160, y=40)

    tk.Label(root, text="Destination Folder").place(x=10, y=80)

    txtDestFolder = tk.Text(root, height=1, width=85)
    txtDestFolder.insert(
        "1.0",
        "optional (if different than source folder)",
    )
    txtDestFolder.place(x=160, y=80)

    tk.Label(root, text="Destination File Name").place(x=10, y=110)

    txtDestFile = tk.Text(root, height=1, width=85)
    txtDestFile.place(x=160, y=110)

    tk.Checkbutton(
        root,
        text="Enable IHO Color Translation",
        variable=enable_translation,
        font=("Segoe UI", 10),
    ).place(x=160, y=140)

    button_config = {
        "font": ("Segoe UI", 13),
        "bg": "#E6E6E6",
        "fg": "#000000",
        "activebackground": "#D0D0D0",
        "activeforeground": "#000000",
        "relief": "raised",
        "borderwidth": 2,
        "highlightthickness": 1,
        "highlightbackground": "#808080",
        "highlightcolor": "#808080",
    }

    frame1 = tk.Frame(root, width=200, height=60)
    frame1.place(x=50, y=160)

    tk.Button(
        frame1,
        text="Select File",
        width=25,
        height=2,
        command=lambda: select_file(
            txtSourceFolder,
            txtSourceFile,
            txtDestFile,
        ),
        **button_config,
    ).pack(expand=True, fill="both")

    frame2 = tk.Frame(root, width=200, height=60)
    frame2.place(x=360, y=160)

    tk.Button(
        frame2,
        text="Select Destination Folder",
        width=25,
        height=2,
        command=lambda: select_dest_folder(txtDestFolder),
        **button_config,
    ).pack(expand=True, fill="both")

    frame3 = tk.Frame(root, width=200, height=60)
    frame3.place(x=50, y=230)

    tk.Button(
        frame3,
        text="Convert",
        width=25,
        height=2,
        command=lambda: convert_svg(
            txtSourceFolder,
            txtSourceFile,
            txtDestFolder,
            txtDestFile,
            enable_translation,
        ),
        **button_config,
    ).pack(expand=True, fill="both")

    frame4 = tk.Frame(root, width=200, height=60)
    frame4.place(x=360, y=230)

    tk.Button(
        frame4,
        text="Quit",
        width=25,
        height=2,
        command=root.quit,
        **button_config,
    ).pack(expand=True, fill="both")

    tk.Label(
        root,
        text=(
            "Warning: 'SVGStyle.css' will be copied "
            "'when IHO color translation is enabled."
        ),
        fg="red",
        font=("Segoe UI", 9, "italic"),
    ).place(x=50, y=310)

    root.mainloop()
