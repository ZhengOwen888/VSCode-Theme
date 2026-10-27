# AK Theme Pack

A collection of custom VSCode color themes.

## About

AK Theme Pack is a collections of color themes that is generated from python scripts that extract colors from an image and match each to specific tokens.

## AI-Assisted Development
AI assisted tools were used when making the python scripts.

## Theme Generation

### 1. Create new Palette
```bash
python3 scripts/build_theme.py --init palettes/my-theme.json
```

This creates a blank palette with all the available color roles. You have to fill in the ones that are marked as required (See `ROLES.md`).

### 2. Extract Colors from Image
```bash
python3 scripts/extract_colors.py artwork.png --k 15
```
This analyzes the image and uses k-means clustering to find the top 15 most dominant colors. This only prints out the colors in hexadecimal so you still have to manually assign the colors.

### 3. Validate your Palette
```bash
python3 scripts/build_theme.py palettes/my-theme.json
```
Checks your palette for missing required colors, invalid hexadecimal values, contrast problems, and overly similar colors. This will not generate any files.

### 4. Generate a Preview
```bash
python3 scripts/build_theme.py \
  palettes/my-theme.json \
  --preview previews/my-theme.png
```
Creates a PNG preview that shows your theme's colors and syntax highlighting.

### 5. Build the Theme and Preview
```bash
python3 scripts/build_theme.py \
  palettes/my-theme.json \
  -o ak-theme-pack/themes/my-theme.json \
  --preview previews/my-theme.png
```

### 6. Register a New Theme
```json
{
  "label": "AK My New Theme",
  "uiTheme": "vs-dark",
  "path": "./themes/my-theme.json"
}
```
Remember to add this inside the package.json file whenever you add a new theme to register it.
Also use the same name for label as the name fields in the generated themes.

## Installation
1. Install the zip.
2. Open the zip.
3. Place the `ak-theme-pack` folder into `/Users/user/.vscode/extensions` (or path to where it lives in your device).
4. Make sure to refresh the `extension.json` file.
5. You can play around with the python scripts to create your own themes.