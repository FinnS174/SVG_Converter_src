from datetime import date

XML_VERSION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

STYLE_SHEET = '<?xml-stylesheet href="SVGStyle.css" type="text/css"?>\n'

TITLE = "S-100 SVG Symbol"
DESCRIPTION = "S-100 SVG symbol converted from source SVG."


def buildTitle(title=TITLE):
    return f"<title>{title}</title>"


def buildDescription(desc=DESCRIPTION):
    return f"<desc>{desc}</desc>"


def buildMetadata(
    publisher="IHO",
    source="S52Preslib4.0",
    format_type="S100SVG",
    version="0.1"
):
    current_date = date.today().strftime("%-m/%-d/%Y")

    return f"""  <metadata>
    <iho:S100SVG xmlns:iho="http://www.iho.int/SVGMetadata">
      <iho:Description publisher="{publisher}" creationDate="{current_date}" source="{source}" format="{format_type}" version="{version}" />
    </iho:S100SVG>
  </metadata>"""


PIVOT_POINT = (
    '<circle class="pivotPoint layout" '
    'fill="none" '
    'cx="0.00" '
    'cy="0.00" '
    'r="0.4" />'
)