# UAF PoC

This PoC reproduces the librsvg use-after-free in [CVE-2026-96889](https://www.cve.org/CVERecord?id=CVE-2026-96889). Affected builds may crash. The RCE payload is not included yet.

[poc-uaf.py](poc-uaf.py) generates the SVG.

## Generate the SVG

Usage:

~~~sh
python3 poc-uaf.py -o uaf.svg
~~~

This writes a 420-byte SVG. The included document declares the same entity name that the outer parser is expanding. You can change that name with `--entity NAME`.

## Other ways to supply the input

The UAF needs the crafted SVG to reach an affected librsvg parser. The script keeps that SVG the same and changes how it is carried:

| Input path | Command | Output |
| --- | --- | --- |
| SVG upload or an image fetched by URL | `python3 poc-uaf.py -o uaf.svg` | Raw SVG file. Serve the same file if the application fetches an image URL. |
| Upload that accepts SVG bytes under a PNG name | `python3 poc-uaf.py -o image.png` | The bytes are still SVG, not PNG. The application may reject them. |
| Field that accepts an image data URL | `python3 poc-uaf.py --carrier data-url -o image-url.txt` | A complete `data:image/svg+xml;base64,...` value. |
| Text inserted unescaped into a child of an SVG | `python3 poc-uaf.py --carrier xml-text --tag title -o title.txt` | An XML fragment that closes and reopens that child around an include. It is not a standalone SVG. |

If an application first fetches an HTML page and then follows its `og:image` URL, serve the generated SVG and point that page's image metadata at it.

The `xml-text` form needs an application that lets text change the generated XML. It does not apply when the application escapes the text. The tag name defaults to `title`; `--tag desc` changes it to `desc`. Other XML contexts may need their own adapter.

For a JSON string value, Base64 text, or URL-encoded field, add `--encode json-string`, `--encode base64`, or `--encode urlencoded` to any of the commands above. For example:

~~~sh
python3 poc-uaf.py --carrier data-url --encode json-string -o image-url.json
~~~

That file contains one JSON string, not a complete request body. Use `-o -` to write any form to stdout. With no `-o`, raw SVG goes to `uaf.svg`; other forms go to stdout.

The markup, including the DTD and XInclude, must reach an affected librsvg build.
