# Theme roles

Fill these in `palette.json`. Roles marked **required** must have a color; every other role can stay `null` and will inherit from its fallback.
A fallback is a design choice: the more roles you leave `null`, the fewer hues the theme uses.

## UI

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `ui_bg` | Editor background | **required** | — |
| `ui_fg` | Default UI text (sidebar, tabs, menus) | **required** | — |
| `ui_accent` | Primary accent: buttons, focus ring, badges, active line number, selection tint | **required** | — |
| `ui_bg_sunken` | Darker chrome: title/activity/status bars, tab strip, menus, hover widgets | darker `ui_bg` | — |
| `ui_bg_raised` | Lighter chrome: sidebar, panel, inactive tabs, inputs | mix(`ui_bg`, `ui_fg`, 0.05) | — |
| `ui_bg_hover` | Hover / current-line / list-selection background | mix(`ui_bg`, `ui_fg`, 0.12) | — |
| `ui_border` | Borders and active indent guide | mix(`ui_bg`, `ui_fg`, 0.22) | — |
| `ui_fg_muted` | Inactive tabs, ignored files, muted UI text | mix(`ui_fg`, `ui_bg`, 0.35) | — |
| `ui_fg_dim` | Descriptions, section titles | mix(`ui_fg`, `ui_bg`, 0.15) | — |
| `ui_line_number` | Inactive line numbers | mix(`ui_fg`, `ui_bg`, 0.6) | — |
| `ui_accent_hover` | Button hover, active link | lighten(`ui_accent`, 0.15) | — |
| `ui_active` | Active tab text/border, selected list text, links, suggest-match highlight | `ui_accent` | — |
| `ui_cursor` | Editor and terminal cursor | `ui_accent_hover` | — |
| `ui_on_accent` | Text drawn on top of ui_accent (buttons, badges) | `ui_bg_sunken` | — |

## Status

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `error` | Errors, invalid code, deleted lines, ANSI red | **required** | — |
| `warning` | Warnings, TODO tags, find-match, deprecated, ANSI yellow | **required** | — |
| `info` | Info diagnostics, word highlight, ANSI blue | **required** | — |
| `success` | Added lines, success, ANSI green | **required** | — |
| `modified` | Modified lines in the gutter | `warning` | — |
| `untracked` | Untracked files | `ansi_magenta` | — |
| `ansi_magenta` | Terminal magenta | `annotation` | — |
| `ansi_cyan` | Terminal cyan | `type` | — |

## Syntax: core

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `keyword` | Declarations and modifiers: fn/def/class/struct/let/const/public/static, primitive types by default, word operators (new, sizeof, typeof) | **required** | 20 scopes |
| `function` | Function names (definitions and calls) | **required** | 4 scopes |
| `string` | String literals and their quotes | **required** | 3 scopes |
| `number` | Numeric literals and CSS units | **required** | 2 scopes |
| `type` | Class/struct/enum/interface/trait/typedef names, library classes | **required** | 14 scopes |
| `comment` | Comments (italic, muted) | **required** | 2 scopes |

## Syntax: keywords

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `keyword_flow` | Control flow: if/else/for/while/return/try/throw/break | `keyword` | 1 scopes |
| `keyword_special` | import/export/include/using/use/package, async/await/yield | `keyword` | 20 scopes |
| `type_builtin` | Primitive/builtin types: int, bool, str, u32, string, void | `keyword` | 13 scopes |
| `variable_special` | this / self / super / cls / arguments (neutral by default; set a color to make them stand out) | `variable` | 3 scopes |
| `macro` | Preprocessor directives and macros: #include, #define, println!, MAX_ROWS | `keyword_special` | 9 scopes |
| `annotation` | Decorators, annotations, attributes: @dataclass, @Override, #[derive], [Serializable] | `keyword_special` | 11 scopes |
| `label` | Rust lifetimes ('a), loop labels, goto labels | `type_param` | 6 scopes |

## Syntax: symbols

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `operator` | Operators: + - = == && -> => | `ui_fg_muted` | 2 scopes |
| `punctuation` | Braces, parens, commas, semicolons, :: and . accessors | `operator` | 4 scopes |

## Syntax: names

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `method` | Method names (member functions) | `function` | 4 scopes |
| `builtin_function` | Library/builtin functions: print, len, malloc, console.log | lighten(`function`, 0.18) | 6 scopes |
| `variable` | Variables and plain identifiers (also sets editor default text) | `ui_fg` | 3 scopes |
| `parameter` | Function parameters | `variable` | 2 scopes |
| `property` | Fields, members, object keys | `variable` | 9 scopes |
| `constant` | User constants and enum members (MAX_SIZE, Color.RED) | `number` | 4 scopes |
| `type_param` | Generic / template parameters (T, K, V) | `type` | 4 scopes |
| `namespace` | Namespaces, modules, packages, scope qualifiers (std::, tui.) | `type` | 8 scopes |
| `import_path` | Header and package paths in include/import: <vector>, java.util.* | `namespace` | 5 scopes |

## Syntax: literals

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `boolean_null` | true / false / null / nil / None / undefined | `number` | 7 scopes |
| `builtin_constant` | Other language/library constants (NaN, NULL, libc/DOM constants) | `boolean_null` | 2 scopes |
| `string_escape` | Escapes (\n), format placeholders (%d, {}), ${} interpolation, HTML entities | lighten(`string`, 0.22) | 7 scopes |
| `regex` | Regular-expression literals | `string` | 4 scopes |
| `docstring` | Python docstrings | `string` | 1 scopes |

## Syntax: comments

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `comment_doc` | Doc comments: ///, /** */, JSDoc/Doxygen tags (italic) | `comment` | 8 scopes |
| `comment_todo` | TODO / FIXME / NOTE tags inside comments (italic) | `warning` | 3 scopes |

## Syntax: web

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `tag` | HTML/XML/JSX tag names | `keyword` | 2 scopes |
| `attribute` | HTML/XML attribute names, JSX props | `parameter` | 1 scopes |
| `css_property` | CSS/SCSS/Less property names | `property` | 1 scopes |
| `css_selector` | CSS classes, ids, pseudo-classes/elements | `tag` | 6 scopes |
| `css_value` | CSS keyword values and colors (flex, #fff, bold) | `string` | 5 scopes |
| `css_variable` | CSS custom properties (--gap) | `constant` | 4 scopes |

## Syntax: data & markup

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `data_key` | JSON / YAML / TOML / INI keys (see json_key_levels for nested coloring) | `property` | 7 scopes |
| `markup_heading` | Markdown headings | `type` | 2 scopes |
| `markup_bold` | Markdown bold (colored, never bold-weight) | `keyword_special` | 2 scopes |
| `markup_italic` | Markdown italic (colored, never italic-style) | `string` | 2 scopes |
| `markup_code` | Markdown inline/fenced code | `string` | 4 scopes |
| `markup_quote` | Markdown blockquotes | `comment` | 2 scopes |
| `markup_link` | Markdown links | `type` | 4 scopes |

## Brackets

| Role | What it colors | Falls back to | Scopes |
|---|---|---|---|
| `bracket_1` | Bracket-pair colorization level 1 (cycles after 6) | `string` | — |
| `bracket_2` | Bracket-pair colorization level 2 (cycles after 6) | `type` | — |
| `bracket_3` | Bracket-pair colorization level 3 (cycles after 6) | `function` | — |
| `bracket_4` | Bracket-pair colorization level 4 (cycles after 6) | `number` | — |
| `bracket_5` | Bracket-pair colorization level 5 (cycles after 6) | `parameter` | — |
| `bracket_6` | Bracket-pair colorization level 6 (cycles after 6) | `keyword_special` | — |

## Optional palette keys

- `json_key_levels`: list of colors for nested JSON key depth (level 0, 1, 2, ...). Omit to color all JSON keys with `data_key`.
- `ui_overrides`: `{"workbench.key": "#rrggbb[aa]"}` for UI keys the kit does not derive (used when normalizing older themes that styled extra widgets).
- `semantic_overrides`: `{"semanticTokenType": "#rrggbb"}` to override the standard semantic-token mapping for one theme.
- `type`: `"dark"` (default) or `"light"`. Derived shades assume dark first; light is untested.
