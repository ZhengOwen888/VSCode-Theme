#!/usr/bin/env python3
"""
Role-based VS Code theme builder.

You fill in COLOR ROLES (palette.json). This script owns everything else:
the TextMate scope lists for many languages, semantic-token colors, the UI
color keys, derived shades, and sanity checks. Same scope map for every theme
=> every theme behaves the same way.

  python build_theme.py --init palette.json               # blank template
  python build_theme.py palette.json -o theme.json        # build theme
  python build_theme.py palette.json -o theme.json --preview preview.png
  python build_theme.py --write-roles ROLES.md            # regenerate role docs
  python build_theme.py --selftest                        # check scope map

Optional dependency for --preview: Pillow.
"""
import argparse, colorsys, json, math, os, re, sys

# ───────────────────────── color helpers ─────────────────────────
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')

def h2r(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def r2h(r): return '#%02x%02x%02x' % tuple(max(0, min(255, round(x))) for x in r)
def mix(a, b, t): return r2h([x + (y - x) * t for x, y in zip(h2r(a), h2r(b))])
def lighten(c, t): return mix(c, '#ffffff', t)
def darken(c, t): return mix(c, '#000000', t)
def alpha(c, a): return c + '%02x' % round(a * 255)

def _lin(c): c /= 255; return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
def luminance(h): r, g, b = map(_lin, h2r(h)); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def lab(h):
    r, g, b = [_lin(x) for x in h2r(h)]
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)

def delta_e(a, b): return math.dist(lab(a), lab(b))
def hsv(h): H, S, V = colorsys.rgb_to_hsv(*[x / 255 for x in h2r(h)]); return H * 360, S, V

# ───────────────────────── role table ─────────────────────────
# fallback: None = REQUIRED | "role" | ("lighten"|"darken", role, amt)
#           | ("mix", roleA, roleB, t) | ("sunken", role)
ROLES = []
def role(key, group, desc, fb, scopes=None, italic=False):
    ROLES.append(dict(key=key, group=group, desc=desc, fb=fb, scopes=scopes or [], italic=italic))

# ---- UI ----
role('ui_bg',          'UI', 'Editor background', None)
role('ui_fg',          'UI', 'Default UI text (sidebar, tabs, menus)', None)
role('ui_accent',      'UI', 'Primary accent: buttons, focus ring, badges, active line number, selection tint', None)
role('ui_bg_sunken',   'UI', 'Darker chrome: title/activity/status bars, tab strip, menus, hover widgets', ('sunken', 'ui_bg'))
role('ui_bg_raised',   'UI', 'Lighter chrome: sidebar, panel, inactive tabs, inputs', ('mix', 'ui_bg', 'ui_fg', 0.05))
role('ui_bg_hover',    'UI', 'Hover / current-line / list-selection background', ('mix', 'ui_bg', 'ui_fg', 0.12))
role('ui_border',      'UI', 'Borders and active indent guide', ('mix', 'ui_bg', 'ui_fg', 0.22))
role('ui_fg_muted',    'UI', 'Inactive tabs, ignored files, muted UI text', ('mix', 'ui_fg', 'ui_bg', 0.35))
role('ui_fg_dim',      'UI', 'Descriptions, section titles', ('mix', 'ui_fg', 'ui_bg', 0.15))
role('ui_line_number', 'UI', 'Inactive line numbers', ('mix', 'ui_fg', 'ui_bg', 0.60))
role('ui_accent_hover','UI', 'Button hover, active link', ('lighten', 'ui_accent', 0.15))
role('ui_active',      'UI', 'Active tab text/border, selected list text, links, suggest-match highlight', 'ui_accent')
role('ui_cursor',      'UI', 'Editor and terminal cursor', 'ui_accent_hover')
role('ui_on_accent',   'UI', 'Text drawn on top of ui_accent (buttons, badges)', 'ui_bg_sunken')

# ---- status ----
role('error',   'Status', 'Errors, invalid code, deleted lines, ANSI red', None)
role('warning', 'Status', 'Warnings, TODO tags, find-match, deprecated, ANSI yellow', None)
role('info',    'Status', 'Info diagnostics, word highlight, ANSI blue', None)
role('success', 'Status', 'Added lines, success, ANSI green', None)
role('modified',  'Status', 'Modified lines in the gutter', 'warning')
role('untracked', 'Status', 'Untracked files', 'ansi_magenta')
role('ansi_magenta', 'Status', 'Terminal magenta', 'annotation')
role('ansi_cyan',    'Status', 'Terminal cyan', 'type')

# ---- core syntax (required) ----
role('keyword',  'Syntax: core', 'Declarations and modifiers: fn/def/class/struct/let/const/public/static, primitive types by default, word operators (new, sizeof, typeof)', None,
 ['keyword', 'keyword.other', 'keyword.declaration', 'storage', 'storage.type', 'storage.modifier',
  'keyword.operator.new', 'keyword.operator.delete', 'keyword.operator.sizeof', 'keyword.operator.alignof',
  'keyword.operator.typeof', 'keyword.operator.typeid', 'keyword.operator.instanceof', 'keyword.operator.expression',
  'keyword.operator.wordlike', 'keyword.operator.logical.python', 'keyword.operator.cast',
  'keyword.control.at-rule', 'punctuation.definition.keyword', 'punctuation.definition.storage.type.objc'])
role('function', 'Syntax: core', 'Function names (definitions and calls)', None,
 ['entity.name.function', 'support.function', 'meta.function-call.generic', 'variable.function'])
role('string',   'Syntax: core', 'String literals and their quotes', None,
 ['string', 'punctuation.definition.string', 'storage.type.string.python'])
role('number',   'Syntax: core', 'Numeric literals and CSS units', None,
 ['constant.numeric', 'keyword.other.unit'])
role('type',     'Syntax: core', 'Class/struct/enum/interface/trait/typedef names, library classes', None,
 ['entity.name.type', 'entity.name.class', 'entity.name.struct', 'entity.name.enum', 'entity.name.union',
  'entity.name.trait', 'entity.other.inherited-class', 'support.class', 'support.type', 'support.type.exception',
  'storage.class', 'storage.type.java', 'storage.type.object.array.java', 'support.class.component'])
role('comment',  'Syntax: core', 'Comments (italic, muted)', None,
 ['comment', 'punctuation.definition.comment'], italic=True)

# ---- keyword family ----
role('keyword_flow',    'Syntax: keywords', 'Control flow: if/else/for/while/return/try/throw/break', 'keyword', ['keyword.control'])
role('keyword_special', 'Syntax: keywords', 'import/export/include/using/use/package, async/await/yield', 'keyword',
 ['keyword.control.import', 'keyword.control.export', 'keyword.control.from', 'keyword.control.as',
  'keyword.other.import', 'keyword.other.package', 'keyword.other.using', 'keyword.other.use',
  'keyword.other.namespace', 'keyword.other.crate', 'keyword.package', 'keyword.import',
  'keyword.control.flow.async', 'keyword.control.flow.await', 'keyword.control.async', 'keyword.control.await',
  'keyword.control.yield', 'keyword.operator.await', 'storage.modifier.async', 'storage.type.function.async'])
role('type_builtin',    'Syntax: keywords', 'Primitive/builtin types: int, bool, str, u32, string, void', 'keyword',
 ['storage.type.built-in', 'storage.type.primitive', 'storage.type.numeric', 'storage.type.string',
  'storage.type.boolean', 'storage.type.core', 'storage.type.rune', 'keyword.type', 'support.type.primitive',
  'support.type.builtin', 'support.type.python', 'entity.name.type.primitive', 'entity.name.type.numeric'])
role('variable_special','Syntax: keywords', 'this / self / super / cls / arguments (neutral by default; set a color to make them stand out)', 'variable',
 ['variable.language', 'variable.parameter.function.language.special', 'variable.parameter.function.language.special.self.python'])
role('macro',           'Syntax: keywords', 'Preprocessor directives and macros: #include, #define, println!, MAX_ROWS', 'keyword_special',
 ['entity.name.function.preprocessor', 'entity.name.function.macro', 'entity.name.other.preprocessor',
  'support.function.macro', 'support.macro', 'keyword.control.directive', 'keyword.preprocessor',
  'punctuation.definition.directive', 'meta.preprocessor'])
role('annotation',      'Syntax: keywords', 'Decorators, annotations, attributes: @dataclass, @Override, #[derive], [Serializable]', 'keyword_special',
 ['meta.decorator', 'meta.function.decorator', 'entity.name.function.decorator', 'punctuation.definition.decorator',
  'storage.type.annotation', 'punctuation.definition.annotation', 'meta.annotation', 'entity.name.type.annotation',
  'meta.attribute.rust', 'punctuation.brackets.attribute', 'punctuation.definition.attribute.rust'])
role('label',           'Syntax: keywords', "Rust lifetimes ('a), loop labels, goto labels", 'type_param',
 ['entity.name.label', 'entity.name.type.lifetime', 'storage.modifier.lifetime', 'punctuation.definition.lifetime',
  'entity.name.lifetime', 'punctuation.definition.label'])

# ---- symbols ----
role('operator',    'Syntax: symbols', 'Operators: + - = == && -> =>', 'ui_fg_muted', ['keyword.operator', 'storage.type.function.arrow'])
role('punctuation', 'Syntax: symbols', 'Braces, parens, commas, semicolons, :: and . accessors', 'operator',
 ['punctuation', 'meta.brace', 'meta.bracket', 'meta.delimiter'])

# ---- names ----
role('method',           'Syntax: names', 'Method names (member functions)', 'function',
 ['entity.name.function.member', 'meta.definition.method entity.name.function', 'meta.method.declaration entity.name.function',
  'variable.function.member'])
role('builtin_function', 'Syntax: names', 'Library/builtin functions: print, len, malloc, console.log', ('lighten', 'function', 0.18),
 ['support.function.builtin', 'support.function.magic', 'support.function.kernel', 'support.function.core',
  'support.function.std', 'support.function.C99'])
role('variable',  'Syntax: names', 'Variables and plain identifiers (also sets editor default text)', 'ui_fg',
 ['variable', 'support.variable', 'entity.name.variable'])
role('parameter', 'Syntax: names', 'Function parameters', 'variable',
 ['variable.parameter', 'entity.name.variable.parameter'])
role('property',  'Syntax: names', 'Fields, members, object keys', 'variable',
 ['variable.other.property', 'variable.other.object.property', 'variable.other.member', 'variable.other.field',
  'meta.property.object', 'meta.object-literal.key', 'entity.name.variable.property', 'entity.name.variable.field',
  'support.variable.property'])
role('constant',  'Syntax: names', 'User constants and enum members (MAX_SIZE, Color.RED)', 'number',
 ['variable.other.constant', 'variable.other.enummember', 'constant.other', 'entity.name.constant'])
role('type_param','Syntax: names', 'Generic / template parameters (T, K, V)', 'type',
 ['entity.name.type.parameter', 'entity.name.type.template', 'entity.name.type.generic', 'storage.type.generic'])
role('namespace', 'Syntax: names', 'Namespaces, modules, packages, scope qualifiers (std::, tui.)', 'type',
 ['entity.name.namespace', 'entity.name.type.namespace', 'entity.name.type.module', 'entity.name.module',
  'entity.name.package', 'entity.name.scope-resolution', 'support.other.namespace', 'support.other.module'])
role('import_path','Syntax: names', 'Header and package paths in include/import: <vector>, java.util.*', 'namespace',
 ['string.quoted.other.lt-gt.include', 'string.quoted.double.include', 'storage.modifier.import.java',
  'storage.modifier.package.java', 'variable.language.wildcard.java'])

# ---- literals ----
role('boolean_null',    'Syntax: literals', 'true / false / null / nil / None / undefined', 'number',
 ['constant.language.boolean', 'constant.language.true', 'constant.language.false', 'constant.language.null',
  'constant.language.nil', 'constant.language.none', 'constant.language.undefined'])
role('builtin_constant','Syntax: literals', 'Other language/library constants (NaN, NULL, libc/DOM constants)', 'boolean_null',
 ['constant.language', 'support.constant'])
role('string_escape',   'Syntax: literals', 'Escapes (\\n), format placeholders (%d, {}), ${} interpolation, HTML entities', ('lighten', 'string', 0.22),
 ['constant.character.escape', 'constant.character.entity', 'constant.character.format', 'constant.other.placeholder',
  'punctuation.definition.template-expression', 'punctuation.section.embedded', 'punctuation.section.interpolation'])
role('regex',           'Syntax: literals', 'Regular-expression literals', 'string',
 ['string.regexp', 'keyword.operator.quantifier.regexp', 'keyword.control.anchor.regexp', 'constant.other.character-class.regexp'])
role('docstring',       'Syntax: literals', 'Python docstrings', 'string', ['string.quoted.docstring'])

# ---- comments ----
role('comment_doc',  'Syntax: comments', 'Doc comments: ///, /** */, JSDoc/Doxygen tags (italic)', 'comment',
 ['comment.block.documentation', 'comment.line.documentation', 'comment.block.javadoc',
  'comment.line.double-slash.documentation', 'storage.type.class.jsdoc', 'entity.name.type.instance.jsdoc',
  'variable.other.jsdoc', 'storage.type.class.doxygen'], italic=True)
role('comment_todo', 'Syntax: comments', 'TODO / FIXME / NOTE tags inside comments (italic)', 'warning',
 ['comment keyword.codetag', 'comment.line keyword', 'comment.block keyword'], italic=True)

# ---- web ----
role('tag',          'Syntax: web', 'HTML/XML/JSX tag names', 'keyword', ['entity.name.tag', 'meta.tag.sgml'])
role('attribute',    'Syntax: web', 'HTML/XML attribute names, JSX props', 'parameter', ['entity.other.attribute-name'])
role('css_property', 'Syntax: web', 'CSS/SCSS/Less property names', 'property', ['support.type.property-name'])
role('css_selector', 'Syntax: web', 'CSS classes, ids, pseudo-classes/elements', 'tag',
 ['entity.other.attribute-name.class.css', 'entity.other.attribute-name.id.css', 'entity.other.attribute-name.pseudo-class',
  'entity.other.attribute-name.pseudo-element', 'entity.other.attribute-name.parent-selector.css', 'punctuation.definition.entity.css'])
role('css_value',    'Syntax: web', 'CSS keyword values and colors (flex, #fff, bold)', 'string',
 ['support.constant.property-value', 'support.constant.color', 'support.constant.font-name', 'support.constant.media', 'constant.other.color'])
role('css_variable', 'Syntax: web', 'CSS custom properties (--gap)', 'constant',
 ['variable.css', 'variable.argument.css', 'variable.scss', 'variable.other.less'])

# ---- data / markup ----
role('data_key',       'Syntax: data & markup', 'JSON / YAML / TOML / INI keys (see json_key_levels for nested coloring)', 'property',
 ['support.type.property-name.json', 'support.type.property-name.toml', 'punctuation.support.type.property-name',
  'entity.name.tag.yaml', 'entity.name.section.group-title', 'entity.other.attribute-name.table', 'keyword.other.definition.ini'])
role('markup_heading', 'Syntax: data & markup', 'Markdown headings', 'type', ['markup.heading', 'punctuation.definition.heading'])
role('markup_bold',    'Syntax: data & markup', 'Markdown bold (colored, never bold-weight)', 'keyword_special', ['markup.bold', 'punctuation.definition.bold'])
role('markup_italic',  'Syntax: data & markup', 'Markdown italic (colored, never italic-style)', 'string', ['markup.italic', 'punctuation.definition.italic'])
role('markup_code',    'Syntax: data & markup', 'Markdown inline/fenced code', 'string',
 ['markup.inline.raw', 'markup.raw.block', 'markup.fenced_code.block', 'punctuation.definition.raw'])
role('markup_quote',   'Syntax: data & markup', 'Markdown blockquotes', 'comment', ['markup.quote', 'punctuation.definition.quote'])
role('markup_link',    'Syntax: data & markup', 'Markdown links', 'type',
 ['markup.underline.link', 'string.other.link', 'punctuation.definition.link', 'punctuation.definition.metadata'])

# ---- brackets ----
for i, fb in enumerate(['string', 'type', 'function', 'number', 'parameter', 'keyword_special'], 1):
    role(f'bracket_{i}', 'Brackets', f'Bracket-pair colorization level {i} (cycles after 6)', fb)

# Scopes that map straight onto status roles
STATUS_SCOPES = [
    ('Invalid / deleted',      'error',   ['invalid', 'invalid.illegal', 'markup.deleted', 'markup.deleted.git_gutter']),
    ('Deprecated / changed',   'warning', ['invalid.deprecated', 'markup.changed', 'markup.changed.git_gutter']),
    ('Inserted',               'success', ['markup.inserted', 'markup.inserted.git_gutter']),
]

# LSP semantic tokens -> roles (clangd, cpptools, Pylance, rust-analyzer, Roslyn, jdtls, ts-server)
SEMANTIC = {
    'namespace': 'namespace', 'class': 'type', 'struct': 'type', 'enum': 'type', 'interface': 'type', 'type': 'type',
    'union': 'type', 'typeAlias': 'type', 'typeParameter': 'type_param', 'lifetime': 'label', 'builtinType': 'type_builtin',
    'parameter': 'parameter', 'variable': 'variable', 'property': 'property', 'enumMember': 'constant',
    'function': 'function', 'method': 'method', 'macro': 'macro', 'decorator': 'annotation', 'label': 'label',
    'selfKeyword': 'variable_special', 'selfTypeKeyword': 'variable_special', 'boolean': 'boolean_null',
    'function.defaultLibrary': 'builtin_function', 'method.defaultLibrary': 'builtin_function',
    'string': 'string', 'number': 'number', 'comment': 'comment', 'operator': 'operator',
}

ROLE_BY_KEY = {r['key']: r for r in ROLES}
REQUIRED = [r['key'] for r in ROLES if r['fb'] is None]

# ───────────────────────── palette resolution ─────────────────────────
class Palette:
    def __init__(self, data):
        self.name = data.get('name', 'custom-theme')
        self.type = data.get('type', 'dark')
        raw = data.get('colors', {})
        unknown = [k for k in raw if k not in ROLE_BY_KEY and not k.startswith('_')]
        if unknown: print('WARNING: unknown role(s) ignored:', ', '.join(unknown), file=sys.stderr)
        self.vals = {}
        for k, v in raw.items():
            if k in ROLE_BY_KEY and v:
                if not HEX.match(v): sys.exit(f'ERROR: {k} = {v!r} is not a #rrggbb hex color')
                self.vals[k] = v.lower()
        missing = [k for k in REQUIRED if k not in self.vals]
        if missing: sys.exit('ERROR: required roles not filled in: ' + ', '.join(missing))
        self.json_levels = [c.lower() for c in data.get('json_key_levels', []) if c]
        self.ui_overrides = {}
        for k, v in data.get('ui_overrides', {}).items():
            if not re.match(r'^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$', v): sys.exit(f'ERROR: ui_overrides[{k!r}] = {v!r} is not #rrggbb or #rrggbbaa')
            self.ui_overrides[k] = v.lower()
        self.semantic_overrides = {}
        for k, v in data.get('semantic_overrides', {}).items():
            if not HEX.match(v): sys.exit(f'ERROR: semantic_overrides[{k!r}] = {v!r} is not #rrggbb')
            self.semantic_overrides[k] = v.lower()
        self.inherited = set(); self._cache = {}

    def __call__(self, key):
        if key in self.vals: return self.vals[key]
        if key in self._cache: return self._cache[key]
        fb = ROLE_BY_KEY[key]['fb']; self.inherited.add(key)
        if isinstance(fb, str): out = self(fb)
        elif fb[0] == 'lighten': out = lighten(self(fb[1]), fb[2])
        elif fb[0] == 'darken':  out = darken(self(fb[1]), fb[2])
        elif fb[0] == 'mix':     out = mix(self(fb[1]), self(fb[2]), fb[3])
        elif fb[0] == 'sunken':
            out = darken(self(fb[1]), 0.28) if self.type == 'dark' else mix(self(fb[1]), self('ui_fg'), 0.04)
        self._cache[key] = out
        return out

def describe_fb(fb):
    if fb is None: return '**required**'
    if isinstance(fb, str): return f'`{fb}`'
    if fb[0] in ('lighten', 'darken'): return f'{fb[0]}(`{fb[1]}`, {fb[2]})'
    if fb[0] == 'mix': return f'mix(`{fb[1]}`, `{fb[2]}`, {fb[3]})'
    if fb[0] == 'sunken': return f'darker `{fb[1]}`'

# ───────────────────────── theme generation ─────────────────────────
def build_token_colors(P):
    out = []
    for r in ROLES:
        if not r['scopes']: continue
        s = {'foreground': P(r['key'])}
        if r['italic']: s['fontStyle'] = 'italic'      # italics only on comment-family roles
        out.append({'name': f"{r['key']} — {r['desc'].split(':')[0][:48]}", 'scope': r['scopes'], 'settings': s})
    for name, key, scopes in STATUS_SCOPES:
        out.append({'name': name, 'scope': scopes, 'settings': {'foreground': P(key)}})
    if P.json_levels:
        base = 'source.json meta.structure.dictionary.json'
        step = ' meta.structure.dictionary.value.json meta.structure.dictionary.json'
        for n, c in enumerate(P.json_levels):
            out.append({'name': f'JSON key level {n}', 'scope': [base + step * n + ' support.type.property-name.json'],
                        'settings': {'foreground': c}})
    return out

def build_ui(P):
    R = P; a = alpha
    bg, sunk, raised, hover, border = R('ui_bg'), R('ui_bg_sunken'), R('ui_bg_raised'), R('ui_bg_hover'), R('ui_border')
    fg, muted, dim, ln = R('ui_fg'), R('ui_fg_muted'), R('ui_fg_dim'), R('ui_line_number')
    acc, acch, act, onacc, cur = R('ui_accent'), R('ui_accent_hover'), R('ui_active'), R('ui_on_accent'), R('ui_cursor')
    err, warn, info, ok, mod, unt = R('error'), R('warning'), R('info'), R('success'), R('modified'), R('untracked')
    guide = mix(bg, fg, 0.07)
    c = {
        'foreground': fg, 'descriptionForeground': dim, 'errorForeground': err, 'focusBorder': acc,
        'icon.foreground': muted, 'selection.background': a(acc, 0.25), 'sash.hoverBorder': acc,
        'widget.shadow': '#00000066', 'textLink.foreground': act, 'textLink.activeForeground': acch,
        'textCodeBlock.background': raised, 'textBlockQuote.background': raised, 'textBlockQuote.border': border,
        'toolbar.hoverBackground': a(hover, 0.5),
        # activity / side / panel / title / status
        'activityBar.background': sunk, 'activityBar.foreground': fg, 'activityBar.inactiveForeground': muted,
        'activityBar.border': border, 'activityBarBadge.background': acc, 'activityBarBadge.foreground': onacc,
        'badge.background': warn, 'badge.foreground': onacc,
        'sideBar.background': raised, 'sideBar.border': border, 'sideBar.foreground': fg,
        'sideBarSectionHeader.background': sunk, 'sideBarSectionHeader.foreground': fg,
        'sideBarSectionHeader.border': border, 'sideBarTitle.foreground': dim,
        'panel.background': raised, 'panel.border': border, 'panelTitle.activeBorder': acc,
        'panelTitle.activeForeground': act, 'panelTitle.inactiveForeground': muted,
        'titleBar.activeBackground': sunk, 'titleBar.activeForeground': fg, 'titleBar.border': border,
        'titleBar.inactiveBackground': raised, 'titleBar.inactiveForeground': muted,
        'statusBar.background': sunk, 'statusBar.foreground': fg, 'statusBar.border': border,
        'statusBar.debuggingBackground': err, 'statusBar.debuggingForeground': onacc,
        'statusBarItem.remoteBackground': acc, 'statusBarItem.remoteForeground': onacc,
        'debugToolBar.background': sunk, 'debugToolBar.border': border,
        'breadcrumb.foreground': muted, 'breadcrumb.focusForeground': fg, 'breadcrumb.activeSelectionForeground': act,
        'notifications.background': sunk, 'notifications.border': border, 'notificationCenterHeader.background': raised,
        'progressBar.background': acc,
        # buttons / inputs / dropdowns / menus / lists
        'button.background': acc, 'button.foreground': onacc, 'button.hoverBackground': acch,
        'button.secondaryBackground': raised,
        'dropdown.background': raised, 'dropdown.foreground': fg, 'dropdown.border': border,
        'input.background': raised, 'input.border': border, 'input.foreground': fg,
        'inputOption.activeBorder': acc, 'inputOption.activeBackground': a(acc, 0.125),
        'menu.background': sunk, 'menu.foreground': fg, 'menu.selectionBackground': a(acc, 0.19), 'menu.border': border,
        'quickInput.background': sunk, 'quickInputList.focusBackground': a(acc, 0.19),
        'list.activeSelectionBackground': a(acc, 0.19), 'list.activeSelectionForeground': act,
        'list.focusBackground': a(acc, 0.125), 'list.highlightForeground': warn,
        'list.hoverBackground': a(hover, 0.5), 'list.inactiveSelectionBackground': a(hover, 0.5),
        'list.errorForeground': err, 'list.warningForeground': warn, 'tree.indentGuidesStroke': border,
        'peekView.border': acc, 'peekViewEditor.background': raised, 'peekViewResult.background': sunk,
        'peekViewTitle.background': sunk,
        'problemsErrorIcon.foreground': err, 'problemsWarningIcon.foreground': warn, 'problemsInfoIcon.foreground': info,
        # tabs
        'editorGroup.border': border, 'editorGroupHeader.tabsBackground': sunk, 'editorGroupHeader.tabsBorder': border,
        'tab.activeBackground': bg, 'tab.activeForeground': act, 'tab.activeBorder': act, 'tab.activeBorderTop': acc,
        'tab.border': raised, 'tab.hoverBackground': a(hover, 0.5), 'tab.inactiveBackground': raised,
        'tab.inactiveForeground': muted,
        # editor
        'editor.background': bg, 'editor.foreground': R('variable'),
        'editor.lineHighlightBackground': a(hover, 0.5), 'editor.lineHighlightBorder': '#00000000',
        'editor.selectionBackground': a(acc, 0.33), 'editor.inactiveSelectionBackground': a(acc, 0.18),
        'editor.selectionHighlightBackground': a(acc, 0.125),
        'editor.wordHighlightBackground': a(info, 0.2), 'editor.wordHighlightStrongBackground': a(info, 0.3),
        'editor.findMatchBackground': a(warn, 0.38), 'editor.findMatchHighlightBackground': a(warn, 0.19),
        'editor.rangeHighlightBackground': a(hover, 0.6),
        'editorCursor.foreground': cur, 'editorWhitespace.foreground': guide,
        'editorIndentGuide.background1': guide, 'editorIndentGuide.activeBackground1': border,
        'editorLineNumber.foreground': ln, 'editorLineNumber.activeForeground': acc,
        'editorLink.activeForeground': act,
        'editorBracketMatch.background': a(acc, 0.2), 'editorBracketMatch.border': a(acc, 0.5),
        'editorBracketHighlight.unexpectedBracket.foreground': err,
        'editorError.foreground': err, 'editorWarning.foreground': warn, 'editorInfo.foreground': info,
        'editorInlayHint.foreground': muted, 'editorInlayHint.background': a(hover, 0.5),
        'editorCodeLens.foreground': muted, 'editorGhostText.foreground': a(muted, 0.6),
        'editorStickyScroll.background': sunk, 'editorStickyScrollHover.background': hover,
        'editorHoverWidget.background': sunk, 'editorHoverWidget.border': border,
        'editorSuggestWidget.background': sunk, 'editorSuggestWidget.border': border,
        'editorSuggestWidget.highlightForeground': act, 'editorSuggestWidget.selectedBackground': hover,
        'editorWidget.background': sunk, 'editorWidget.border': border,
        'editorGutter.addedBackground': ok, 'editorGutter.deletedBackground': err, 'editorGutter.modifiedBackground': mod,
        'editorOverviewRuler.border': border, 'editorOverviewRuler.modifiedForeground': mod,
        'editorOverviewRuler.addedForeground': ok, 'editorOverviewRuler.deletedForeground': err,
        'editorOverviewRuler.errorForeground': err, 'editorOverviewRuler.warningForeground': warn,
        'minimap.errorHighlight': err, 'minimap.warningHighlight': warn, 'minimap.selectionHighlight': a(acc, 0.4),
        'minimapGutter.addedBackground': ok, 'minimapGutter.modifiedBackground': mod, 'minimapGutter.deletedBackground': err,
        'diffEditor.insertedTextBackground': a(ok, 0.15), 'diffEditor.removedTextBackground': a(err, 0.15),
        'scrollbarSlider.background': a(border, 0.25), 'scrollbarSlider.hoverBackground': a(border, 0.38),
        'scrollbarSlider.activeBackground': a(acc, 0.19),
        # git
        'gitDecoration.addedResourceForeground': ok, 'gitDecoration.modifiedResourceForeground': mod,
        'gitDecoration.deletedResourceForeground': err, 'gitDecoration.untrackedResourceForeground': unt,
        'gitDecoration.ignoredResourceForeground': muted, 'gitDecoration.conflictingResourceForeground': warn,
        # terminal
        'terminal.background': bg, 'terminal.foreground': fg, 'terminalCursor.foreground': cur,
        'terminal.selectionBackground': a(acc, 0.25),
        'terminal.ansiBlack': bg, 'terminal.ansiRed': err, 'terminal.ansiGreen': ok, 'terminal.ansiYellow': warn,
        'terminal.ansiBlue': info, 'terminal.ansiMagenta': R('ansi_magenta'), 'terminal.ansiCyan': R('ansi_cyan'),
        'terminal.ansiWhite': fg, 'terminal.ansiBrightBlack': muted,
        'terminal.ansiBrightRed': lighten(err, 0.15), 'terminal.ansiBrightGreen': lighten(ok, 0.15),
        'terminal.ansiBrightYellow': lighten(warn, 0.15), 'terminal.ansiBrightBlue': lighten(info, 0.15),
        'terminal.ansiBrightMagenta': lighten(R('ansi_magenta'), 0.15), 'terminal.ansiBrightCyan': lighten(R('ansi_cyan'), 0.15),
        'terminal.ansiBrightWhite': lighten(fg, 0.1),
    }
    for i in range(1, 7): c[f'editorBracketHighlight.foreground{i}'] = R(f'bracket_{i}')
    return c

def build_theme(P):
    colors = build_ui(P); colors.update(P.ui_overrides)          # per-theme extras the kit does not derive
    semantic = {k: P(v) for k, v in SEMANTIC.items()}; semantic.update(P.semantic_overrides)
    return {'$schema': 'vscode://schemas/color-theme', 'name': P.name, 'type': P.type,
            'semanticHighlighting': True, 'semanticTokenColors': semantic,
            'colors': colors, 'tokenColors': build_token_colors(P)}

# ───────────────────────── checks ─────────────────────────
MUST_DIFFER = [('keyword', 'function'), ('keyword', 'type'), ('function', 'type'), ('keyword', 'string'),
               ('string', 'number'), ('function', 'string'), ('parameter', 'string'), ('variable', 'parameter'),
               ('keyword', 'number'), ('type', 'string'), ('function', 'number'), ('operator', 'variable'),
               ('keyword_special', 'keyword'), ('comment', 'operator')]

def report(P):
    bg = P('ui_bg'); lines = []; syntax = [r['key'] for r in ROLES if r['group'].startswith('Syntax')]
    for k in syntax:
        c = P(k); cr = contrast(c, bg); floor = 3.0 if k.startswith('comment') or k == 'markup_quote' else 4.5
        if cr < floor: lines.append(f'  low contrast  {k:18s} {c} {cr:.1f}:1 (want >= {floor})')
    for a, b in MUST_DIFFER:
        d = delta_e(P(a), P(b))
        if d < 15: lines.append(f'  too similar   {a} vs {b}: {P(a)} / {P(b)} (deltaE {d:.0f}, want >= 15)')
    buckets = {round(hsv(P(k))[0] / 30) % 12 for k in syntax if hsv(P(k))[1] > 0.25}
    lines.append(f'  hue families among syntax roles: {len(buckets)}')
    lines.append(f'  {len(P.vals)} roles filled, {len(P.inherited)} inherited from fallbacks')
    if P.ui_overrides or P.semantic_overrides:
        lines.append(f'  carried per-theme extras: {len(P.ui_overrides)} ui_overrides, {len(P.semantic_overrides)} semantic_overrides')
    return lines

def selftest():
    seen = {}; bad = 0
    for r in ROLES:
        for s in r['scopes']:
            if s in seen: print(f'DUPLICATE scope {s!r}: {seen[s]} and {r["key"]}'); bad += 1
            seen[s] = r['key']
    for _, key, scopes in STATUS_SCOPES:
        for s in scopes:
            if s in seen: print(f'DUPLICATE scope {s!r}: {seen[s]} and {key}'); bad += 1
            seen[s] = key
    for v in SEMANTIC.values():
        if v not in ROLE_BY_KEY: print('semantic map refers to unknown role', v); bad += 1
    for r in ROLES:
        fb = r['fb']; refs = [] if fb is None else [fb] if isinstance(fb, str) else [x for x in fb[1:3] if isinstance(x, str)]
        for x in refs:
            if x not in ROLE_BY_KEY: print('unknown fallback', x, 'in', r['key']); bad += 1
    print(f'selftest: {len(ROLES)} roles, {len(seen)} scopes, {bad} problems'); return bad == 0

# ───────────────────────── docs / init ─────────────────────────
def write_roles_md(path):
    L = ['# Theme roles', '',
         'Fill these in `palette.json`. Roles marked **required** must have a color; every other role can stay `null` and will inherit from its fallback.',
         'A fallback is a design choice: the more roles you leave `null`, the fewer hues the theme uses.', '']
    groups = []
    for r in ROLES:
        if r['group'] not in groups: groups.append(r['group'])
    for g in groups:
        L += [f'## {g}', '', '| Role | What it colors | Falls back to | Scopes |', '|---|---|---|---|']
        for r in ROLES:
            if r['group'] != g: continue
            sc = f"{len(r['scopes'])} scopes" if r['scopes'] else '—'
            L.append(f"| `{r['key']}` | {r['desc']} | {describe_fb(r['fb'])} | {sc} |")
        L.append('')
    L += ['## Optional palette keys', '',
          '- `json_key_levels`: list of colors for nested JSON key depth (level 0, 1, 2, ...). Omit to color all JSON keys with `data_key`.',
          '- `ui_overrides`: `{"workbench.key": "#rrggbb[aa]"}` for UI keys the kit does not derive (used when normalizing older themes that styled extra widgets).',
          '- `semantic_overrides`: `{"semanticTokenType": "#rrggbb"}` to override the standard semantic-token mapping for one theme.',
          '- `type`: `"dark"` (default) or `"light"`. Derived shades assume dark first; light is untested.', '']
    open(path, 'w').write('\n'.join(L))

def write_init(path):
    colors = {}
    for r in ROLES: colors[r['key']] = None
    ordered = {k: None for k in REQUIRED}; ordered.update({k: None for k in colors if k not in ordered})
    json.dump({'_help': 'Fill every role listed first (required). Leave others null to inherit. See ROLES.md.',
               'name': 'my-theme', 'type': 'dark', 'colors': ordered, 'json_key_levels': []},
              open(path, 'w'), indent=2)
    open(path, 'a').write('\n')

# ───────────────────────── preview ─────────────────────────
ALIAS = dict(kw='keyword', kf='keyword_flow', ks='keyword_special', tb='type_builtin', vs='variable_special', ma='macro',
             an='annotation', la='label', op='operator', pu='punctuation', me='method', bf='builtin_function', fn='function',
             va='variable', pa='parameter', pr='property', co='constant', tp='type_param', ns='namespace', ip='import_path',
             bo='boolean_null', bc='builtin_constant', se='string_escape', st='string', dc='docstring', cd='comment_doc',
             cm='comment', ty='type', nu='number', ta='tag', at='attribute', cp='css_property', cs='css_selector',
             cv='css_value', cx='css_variable', dk='data_key', mh='markup_heading', mb='markup_bold', mi='markup_italic',
             mc='markup_code', mq='markup_quote', ml='markup_link', rx='regex')
SNIPPETS = [
 ('C++', ['⟦cd|/// Draw one frame.⟧', '⟦ma|#include⟧ ⟦ip|<vector>⟧', '⟦ma|#define⟧ ⟦ma|MAX_ROWS⟧ ⟦nu|64⟧',
  '⟦kw|template⟧⟦pu|<⟧⟦kw|typename⟧ ⟦tp|T⟧⟦pu|>⟧', '⟦kw|class⟧ ⟦ty|Screen⟧ ⟦pu|{⟧', '⟦kw|public⟧⟦pu|:⟧',
  '  ⟦tb|void⟧ ⟦me|flush⟧⟦pu|(⟧⟦kw|const⟧ ⟦ty|Cell⟧⟦op|&⟧ ⟦pa|c⟧⟦pu|,⟧ ⟦tb|int⟧ ⟦pa|rows⟧⟦pu|)⟧ ⟦pu|{⟧',
  '    ⟦kf|if⟧ ⟦pu|(⟧rows ⟦op|>⟧ ⟦nu|0⟧⟦pu|)⟧ ⟦pu|{⟧', '      ⟦vs|this⟧⟦pu|->⟧⟦pr|buf_⟧⟦pu|.⟧⟦me|write⟧⟦pu|(⟧⟦st|"⟧⟦se|\\x1b⟧⟦st|[2J"⟧⟦pu|,⟧ ⟦bc|nullptr⟧⟦pu|);⟧',
  '    ⟦pu|}⟧ ⟦kf|return⟧⟦pu|;⟧']),
 ('Python', ['⟦ks|from⟧ ⟦ns|pathlib⟧ ⟦ks|import⟧ ⟦ty|Path⟧', '⟦an|@dataclass⟧', '⟦kw|class⟧ ⟦ty|Config⟧⟦pu|(⟧⟦ty|Base⟧⟦pu|):⟧',
  '    ⟦dc|"""Load settings."""⟧', '    ⟦kw|def⟧ ⟦me|load⟧⟦pu|(⟧⟦vs|self⟧⟦pu|,⟧ ⟦pa|path⟧⟦pu|:⟧ ⟦tb|str⟧ ⟦op|=⟧ ⟦st|"a.toml"⟧⟦pu|):⟧',
  '        ⟦cm|# TODO: validate⟧', '        ⟦kf|with⟧ ⟦bf|open⟧⟦pu|(⟧path⟦pu|)⟧ ⟦kf|as⟧ f⟦pu|:⟧',
  '            ⟦kf|return⟧ ⟦fn|parse⟧⟦pu|(⟧f⟦pu|.⟧⟦me|read⟧⟦pu|(),⟧ ⟦pa|strict⟧⟦op|=⟧⟦bo|True⟧⟦pu|)⟧',
  '        ⟦st|f"⟧⟦se|{⟧n⟦se|}⟧⟦st| rows"⟧ ⟦kf|if⟧ n ⟦kw|and⟧ ⟦bo|None⟧']),
 ('Rust', ['⟦ks|use⟧ ⟦ns|std⟧⟦pu|::⟧⟦ns|io⟧⟦pu|;⟧', '⟦an|#[derive(Debug)]⟧', '⟦kw|struct⟧ ⟦ty|Frame⟧⟦pu|<⟧⟦la|\'a⟧⟦pu|> {⟧',
  '    ⟦kw|pub⟧ ⟦pr|rows⟧⟦pu|:⟧ ⟦tb|u32⟧⟦pu|,⟧', '    ⟦kw|pub⟧ ⟦pr|buf⟧⟦pu|:⟧ ⟦op|&⟧⟦la|\'a⟧ ⟦tb|str⟧⟦pu|,⟧', '⟦pu|}⟧',
  '⟦kw|impl⟧⟦pu|<⟧⟦la|\'a⟧⟦pu|>⟧ ⟦ty|Frame⟧⟦pu|<⟧⟦la|\'a⟧⟦pu|> {⟧', '    ⟦kw|pub fn⟧ ⟦fn|draw⟧⟦pu|(⟧⟦vs|&self⟧⟦pu|)⟧ ⟦op|->⟧ ⟦ty|Result⟧⟦pu|<(),⟧ ⟦ty|Error⟧⟦pu|> {⟧',
  '        ⟦ma|println!⟧⟦pu|(⟧⟦st|"rows=⟧⟦se|{}⟧⟦st|"⟧⟦pu|,⟧ ⟦vs|self⟧⟦pu|.⟧⟦pr|rows⟧⟦pu|);⟧', '        ⟦ty|Ok⟧⟦pu|(())⟧']),
 ('TypeScript', ['⟦ks|import⟧ ⟦pu|{⟧ ⟦ty|Router⟧ ⟦pu|}⟧ ⟦ks|from⟧ ⟦st|\'./router\'⟧⟦pu|;⟧', '⟦kw|const⟧ ⟦co|MAX⟧ ⟦op|=⟧ ⟦nu|42⟧⟦pu|;⟧',
  '⟦kw|interface⟧ ⟦ty|Opts⟧ ⟦pu|{⟧ ⟦pr|retries⟧⟦pu|:⟧ ⟦tb|number⟧ ⟦pu|}⟧', '⟦ks|async⟧ ⟦kw|function⟧ ⟦fn|load⟧⟦pu|<⟧⟦tp|T⟧⟦pu|>(⟧⟦pa|url⟧⟦pu|:⟧ ⟦tb|string⟧⟦pu|) {⟧',
  '  ⟦kw|const⟧ res ⟦op|=⟧ ⟦ks|await⟧ ⟦fn|fetch⟧⟦pu|(⟧⟦st|`/api/⟧⟦se|${⟧url⟦se|}⟧⟦st|`⟧⟦pu|);⟧',
  '  ⟦kf|if⟧ ⟦pu|(!⟧res⟦pu|.⟧⟦pr|ok⟧⟦pu|)⟧ ⟦kf|throw⟧ ⟦kw|new⟧ ⟦ty|Error⟧⟦pu|(⟧⟦st|"bad"⟧⟦pu|);⟧',
  '  ⟦kf|return⟧ res⟦pu|.⟧⟦me|json⟧⟦pu|();⟧ ⟦cm|// ok⟧', '⟦pu|}⟧', '⟦kw|const⟧ r ⟦op|=⟧ ⟦rx|/^a+$/g⟧⟦pu|;⟧ ⟦bo|null⟧ ⟦bo|true⟧']),
 ('Java', ['⟦ks|package⟧ ⟦ip|com.example.app⟧⟦pu|;⟧', '⟦ks|import⟧ ⟦ip|java.util.List⟧⟦pu|;⟧', '⟦an|@Override⟧',
  '⟦kw|public class⟧ ⟦ty|Screen⟧ ⟦kw|extends⟧ ⟦ty|Base⟧ ⟦pu|{⟧', '  ⟦kw|private final⟧ ⟦ty|List⟧⟦pu|<⟧⟦ty|String⟧⟦pu|>⟧ ⟦pr|rows⟧⟦pu|;⟧',
  '  ⟦kw|public⟧ ⟦tb|void⟧ ⟦me|flush⟧⟦pu|(⟧⟦tb|int⟧ ⟦pa|n⟧⟦pu|) {⟧', '    ⟦kf|for⟧ ⟦pu|(⟧⟦tb|int⟧ i ⟦op|=⟧ ⟦nu|0⟧⟦pu|;⟧ i ⟦op|<⟧ n⟦pu|;⟧ i⟦op|++⟧⟦pu|)⟧ ⟦pu|{⟧',
  '      ⟦ty|System⟧⟦pu|.⟧⟦pr|out⟧⟦pu|.⟧⟦me|println⟧⟦pu|(⟧⟦st|"row\\n"⟧⟦pu|);⟧', '    ⟦pu|}⟧ ⟦pu|}⟧']),
 ('Objective-C', ['⟦ma|#import⟧ ⟦ip|<Foundation/Foundation.h>⟧', '⟦kw|@interface⟧ ⟦ty|MCCApp⟧ ⟦pu|:⟧ ⟦ty|NSObject⟧', '⟦kw|@property⟧ ⟦pu|(⟧⟦kw|nonatomic⟧⟦pu|)⟧ ⟦ty|NSString⟧ ⟦op|*⟧⟦pr|name⟧⟦pu|;⟧',
  '⟦kw|@end⟧', '⟦kw|@implementation⟧ ⟦ty|MCCApp⟧', '⟦pu|-⟧ ⟦pu|(⟧⟦tb|void⟧⟦pu|)⟧⟦me|show⟧⟦pu|:⟧⟦pu|(⟧⟦ty|NSString⟧ ⟦op|*⟧⟦pu|)⟧⟦pa|msg⟧ ⟦pu|{⟧',
  '  ⟦bf|NSLog⟧⟦pu|(⟧⟦st|@"hi %@"⟧⟦pu|,⟧ msg⟦pu|);⟧', '  ⟦pu|[⟧⟦vs|self⟧ ⟦me|reload⟧⟦pu|];⟧ ⟦bc|nil⟧ ⟦bo|YES⟧', '⟦pu|}⟧']),
 ('HTML + CSS', ['⟦pu|<⟧⟦ta|div⟧ ⟦at|class⟧⟦op|=⟧⟦st|"card"⟧ ⟦at|id⟧⟦op|=⟧⟦st|"main"⟧⟦pu|>⟧', '  ⟦pu|<⟧⟦ta|h1⟧⟦pu|>⟧Title ⟦se|&amp;⟧ more⟦pu|</⟧⟦ta|h1⟧⟦pu|>⟧',
  '⟦pu|</⟧⟦ta|div⟧⟦pu|>⟧', '⟦kw|@media⟧ ⟦pu|(⟧⟦cp|min-width⟧⟦pu|:⟧ ⟦nu|600px⟧⟦pu|) {⟧', '⟦cs|.card⟧⟦pu|:⟧⟦cs|hover⟧ ⟦pu|{⟧',
  '  ⟦cx|--gap⟧⟦pu|:⟧ ⟦nu|8px⟧⟦pu|;⟧', '  ⟦cp|color⟧⟦pu|:⟧ ⟦cv|#52d3c6⟧⟦pu|;⟧', '  ⟦cp|display⟧⟦pu|:⟧ ⟦cv|flex⟧⟦pu|;⟧ ⟦cp|margin⟧⟦pu|:⟧ ⟦fn|calc⟧⟦pu|(⟧⟦fn|var⟧⟦pu|(⟧⟦cx|--gap⟧⟦pu|))⟧⟦pu|;⟧', '⟦pu|} }⟧']),
 ('JSON + Markdown', ['⟦pu|{⟧', '  ⟦dk|"name"⟧⟦pu|:⟧ ⟦st|"crimson"⟧⟦pu|,⟧', '  ⟦dk|"size"⟧⟦pu|:⟧ ⟦nu|12⟧⟦pu|,⟧ ⟦dk|"on"⟧⟦pu|:⟧ ⟦bo|true⟧', '⟦pu|}⟧',
  '⟦mh|# Heading⟧', 'Some ⟦mb|**bold**⟧ and ⟦mi|*italic*⟧ and ⟦mc|`code`⟧', '⟦ml|[link](https://x.dev)⟧', '⟦mq|> a quote⟧', '⟦kw|SELECT⟧ ⟦pu|*⟧ ⟦kw|FROM⟧ t ⟦kw|WHERE⟧ id ⟦op|=⟧ ⟦nu|1⟧']),
]

def render_preview(P, path):
    try: from PIL import Image, ImageDraw, ImageFont
    except ImportError: sys.exit('--preview needs Pillow: pip install pillow')
    fp = next((p for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', '/System/Library/Fonts/Menlo.ttc',
                           '/Library/Fonts/Menlo.ttc', 'C:/Windows/Fonts/consola.ttf'] if os.path.exists(p)), None)
    F = lambda n: ImageFont.truetype(fp, n) if fp else ImageFont.load_default()
    f, fs = F(14), F(12)
    bg, fg, ln, muted = P('ui_bg'), P('variable'), P('ui_line_number'), P('ui_fg_muted')
    syn = [r['key'] for r in ROLES if r['group'].startswith('Syntax')]
    cols, cw, W = 5, 296, 1500
    rows_sw = math.ceil(len(syn) / cols); pw, ph = 730, 14 + 10 * 22 + 34; gridy = 56 + rows_sw * 24 + 18
    H = gridy + 4 * (ph + 14) + 10
    im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
    d.text((20, 14), f'{P.name}  |  swatches resolved on {bg}  ( ~ = inherited from fallback )', font=F(16), fill=P('ui_fg'))
    for i, k in enumerate(syn):
        x, y = 20 + (i % cols) * cw, 46 + (i // cols) * 24
        d.rectangle((x, y, x + 20, y + 17), fill=P(k))
        d.text((x + 26, y + 2), f"{k}{'~' if k in P.inherited else ''}  {P(k)}", font=fs, fill=P(k))
    pat = re.compile(r'⟦(\w+)\|(.*?)⟧'); cwid = f.getlength('M')
    for n, (title, lines) in enumerate(SNIPPETS):
        ox, oy = 20 + (n % 2) * (pw + 10), gridy + (n // 2) * (ph + 14)
        d.rectangle((ox, oy, ox + pw, oy + ph), fill=P('ui_bg'), outline=P('ui_border'))
        d.text((ox + 10, oy + 6), title, font=fs, fill=muted)
        for i, line in enumerate(lines[:10]):
            y = oy + 30 + i * 22; d.text((ox + 10, y), f'{i + 1:2d}', font=f, fill=ln); x = ox + 46; pos = 0
            for m in list(pat.finditer(line)) + [None]:
                plain = line[pos:m.start()] if m else line[pos:]
                if plain: d.text((x, y), plain, font=f, fill=fg); x += cwid * len(plain)
                if m:
                    key = ALIAS[m.group(1)]; d.text((x, y), m.group(2), font=f, fill=P(key)); x += cwid * len(m.group(2)); pos = m.end()
    im.save(path)

# ───────────────────────── CLI ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('palette', nargs='?'); ap.add_argument('-o', '--out')
    ap.add_argument('--init', metavar='FILE'); ap.add_argument('--preview', metavar='PNG')
    ap.add_argument('--write-roles', metavar='MD'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(0 if selftest() else 1)
    if a.write_roles: write_roles_md(a.write_roles); print('wrote', a.write_roles); return
    if a.init: write_init(a.init); print('wrote blank palette', a.init); return
    if not a.palette: ap.error('give a palette.json (or --init / --write-roles / --selftest)')
    P = Palette(json.load(open(a.palette)))
    if a.preview: render_preview(P, a.preview); print('wrote preview', a.preview)
    print('checks:'); print('\n'.join(report(P)))
    if a.out:
        json.dump(build_theme(P), open(a.out, 'w'), indent=2, ensure_ascii=False); open(a.out, 'a').write('\n')
        print('wrote theme', a.out)

if __name__ == '__main__': main()
