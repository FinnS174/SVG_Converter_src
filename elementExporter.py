import os

PADDING = 1

# Target coordinate system used by the Symbol Builder
TARGET_WIDTH = 9.4
TARGET_HEIGHT = 9.61
TARGET_X = -4.73
TARGET_Y = -5.12


def write_svg_header(f, width, height):
    f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
    f.write('<?xml-stylesheet href="style.css" type="text/css"?>\n')
    f.write(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'version="1.2" baseProfile="tiny" '
    )
    f.write(
        f'width="{width}mm" '
        f'height="{height}mm" '
        f'viewBox="{TARGET_X} {TARGET_Y} '
        f'{TARGET_WIDTH} {TARGET_HEIGHT}">\n'
    )


def write_svg_footer(f):
    f.write('</svg>\n')


def export_individual_svgs(
    elements,
    output_dir,
    logical_width=78.33,
    logical_height=90.63
):
    os.makedirs(output_dir, exist_ok=True)

    for idx, element in enumerate(elements):
        filename = os.path.join(
            output_dir,
            f"element_{idx + 1}.svg"
        )

        # Scale the existing source coordinate system
        # into the Symbol Builder coordinate system.
        scale_x = TARGET_WIDTH / logical_width
        scale_y = TARGET_HEIGHT / logical_height

        with open(filename, 'w') as f:
            write_svg_header(
                f,
                TARGET_WIDTH,
                TARGET_HEIGHT
            )

            f.write(
                f'  <g transform="'
                f'translate({TARGET_X},{TARGET_Y}) '
                f'scale({scale_x},{scale_y})">\n'
            )

            f.write(f"    {str(element)}\n")
            f.write("  </g>\n")

            write_svg_footer(f)

    print(
        f"Exported {len(elements)} individual SVG files "
        f"to {output_dir}"
    )