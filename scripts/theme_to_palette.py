#!/usr/bin/env python3
"""
Normalize existing VS Code themes into the role-based kit.

  python theme_to_palette.py old1.json old2.json ... -o outdir

For each theme writes, under outdir/:
  palettes/<name>.palette.json   the inferred role palette (inherited roles left null)
  themes/<name>.json             the theme rebuilt by build_theme.py
  previews/<name>.png            role swatches + code panels on the theme's own background
and one REPORT.md covering what was merged, carried over, or changed.

How it works: every role has a few "probe" scopes. The old theme is asked what color a
token with that scope would get (TextMate-style prefix matching, longest selector wins).
Roles whose color equals what they would inherit anyway are dropped, so palettes stay minimal.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_theme as B

# ───────────── old-theme scope resolution ─────────────
def prefix_match(sel, scope): return scope == sel or scope.startswith(sel + '.')

def norm_hex(c):
    if not isinstance(c, str) or not c.startswith('#'): return None
    h = c[1:].lower()
    if len(h) in (3, 4): h = ''.join(ch * 2 for ch in h)
    return '#' + h if len(h) in (6, 8) and re.fullmatch(r'[0-9a-f]+', h) else None

def rgb6(c): return c[:7] if c else None
def alpha_of(c): return int(c[7:9], 16) if c and len(c) == 9 else 255

class OldTheme:
    def __init__(self, data):
        self.data = data; self.rules = []; self.styled = []
        for i, r in enumerate(data.get('tokenColors', [])):
            st = r.get('settings', {}); sc = r.get('scope', [])
            sels = [x.strip() for x in (sc if isinstance(sc, list) else sc.split(','))] if sc else []
            fs = (st.get('fontStyle') or '').strip()
            if fs: self.styled.append((r.get('name') or (sels[0] if sels else '?'), fs))
            fg = norm_hex(st.get('foreground')); 
            for s in sels:
                if not s or not fg: continue
                parts = s.split()
                self.rules.append((i, parts[:-1], parts[-1], rgb6(fg)))

    def resolve(self, stack):
        """-> (segments, ancestors, color) of the most specific matching rule, or None"""
        best = None
        for i, anc, leaf, fg in self.rules:
            if not prefix_match(leaf, stack[-1]): continue
            pos, ok = 0, True
            for a in anc:
                while pos < len(stack) - 1 and not prefix_match(a, stack[pos]): pos += 1
                if pos >= len(stack) - 1: ok = False; break
                pos += 1
            if not ok: continue
            key = (leaf.count('.') + 1, len(anc), i)
            if best is None or key > best[0]: best = (key, fg)
        return (best[0][0], best[0][1], best[1]) if best else None

# role -> probe scopes (a probe with spaces is an ancestor stack: "ancestor leaf")
PROBES = {
 'keyword': ['storage.type', 'storage.modifier', 'keyword.other'], 'function': ['entity.name.function'],
 'string': ['string.quoted.double', 'string'], 'number': ['constant.numeric'],
 'type': ['entity.name.type', 'entity.name.class', 'support.class'], 'comment': ['comment.line', 'comment'],
 'keyword_flow': ['keyword.control'],
 'keyword_special': ['keyword.control.import', 'keyword.other.using', 'keyword.other.import', 'storage.modifier.async', 'keyword.control.flow.await'],
 'type_builtin': ['storage.type.primitive', 'storage.type.built-in', 'support.type.primitive', 'keyword.type'],
 'variable_special': ['variable.language.this', 'variable.language.self', 'variable.language'],
 'macro': ['entity.name.function.preprocessor', 'keyword.control.directive', 'meta.preprocessor'],
 'annotation': ['entity.name.function.decorator', 'meta.decorator', 'storage.type.annotation', 'meta.attribute.rust'],
 'label': ['entity.name.label', 'entity.name.type.lifetime', 'storage.modifier.lifetime'],
 'operator': ['keyword.operator.assignment', 'keyword.operator'], 'punctuation': ['punctuation.separator.comma', 'punctuation', 'meta.brace'],
 'method': ['entity.name.function.member', 'meta.method.declaration entity.name.function'],
 'builtin_function': ['support.function.builtin', 'support.function.magic', 'support.function'],
 'variable': ['variable.other.readwrite', 'variable.other', 'variable'],
 'parameter': ['variable.parameter', 'variable.parameter.function'],
 'property': ['variable.other.property', 'variable.other.member', 'meta.object-literal.key', 'entity.name.property'],
 'constant': ['variable.other.constant', 'variable.other.enummember', 'constant.other'],
 'type_param': ['entity.name.type.parameter', 'entity.name.type.template'],
 'namespace': ['entity.name.namespace', 'entity.name.type.namespace', 'entity.name.scope-resolution'],
 'import_path': ['string.quoted.other.lt-gt.include', 'storage.modifier.import.java'],
 'boolean_null': ['constant.language.boolean', 'constant.language.null'], 'builtin_constant': ['constant.language', 'support.constant'],
 'string_escape': ['constant.character.escape', 'punctuation.definition.template-expression'],
 'regex': ['string.regexp'], 'docstring': ['string.quoted.docstring.multi.python', 'string.quoted.docstring'],
 'comment_doc': ['comment.block.documentation'], 'comment_todo': ['comment keyword.codetag'],
 'tag': ['entity.name.tag'], 'attribute': ['entity.other.attribute-name'],
 'css_property': ['source.css support.type.property-name.css'], 'css_selector': ['entity.other.attribute-name.class.css'],
 'css_value': ['support.constant.property-value.css'], 'css_variable': ['variable.css', 'variable.argument.css'],
 'data_key': ['source.json meta.structure.dictionary.json support.type.property-name.json'],
 'markup_heading': ['markup.heading', 'entity.name.section'], 'markup_bold': ['markup.bold'], 'markup_italic': ['markup.italic'],
 'markup_code': ['markup.inline.raw', 'markup.raw.block'], 'markup_quote': ['markup.quote'],
 'markup_link': ['markup.underline.link', 'string.other.link.title.markdown'],
}
# role -> old workbench color keys, first present wins
UI_PROBES = {
 'ui_bg': ['editor.background'], 'ui_fg': ['foreground', 'sideBar.foreground', 'editor.foreground'],
 'ui_accent': ['focusBorder', 'button.background', 'activityBarBadge.background', 'editorLineNumber.activeForeground', 'tab.activeBorderTop'],
 'ui_bg_sunken': ['activityBar.background', 'statusBar.background', 'titleBar.activeBackground'],
 'ui_bg_raised': ['sideBar.background', 'panel.background', 'tab.inactiveBackground'],
 'ui_border': ['panel.border', 'sideBar.border', 'editorGroup.border'],
 'ui_fg_muted': ['tab.inactiveForeground', 'activityBar.inactiveForeground'],
 'ui_fg_dim': ['descriptionForeground', 'sideBarTitle.foreground'], 'ui_line_number': ['editorLineNumber.foreground'],
 'ui_accent_hover': ['button.hoverBackground'], 'ui_active': ['tab.activeForeground', 'tab.activeBorder', 'textLink.foreground', 'list.activeSelectionForeground'],
 'ui_cursor': ['editorCursor.foreground'], 'ui_on_accent': ['button.foreground', 'activityBarBadge.foreground'],
 'error': ['editorError.foreground', 'errorForeground', 'terminal.ansiRed'], 'warning': ['editorWarning.foreground', 'terminal.ansiYellow', 'list.warningForeground'],
 'info': ['editorInfo.foreground', 'terminal.ansiBlue'], 'success': ['gitDecoration.addedResourceForeground', 'editorGutter.addedBackground', 'terminal.ansiGreen'],
 'modified': ['gitDecoration.modifiedResourceForeground', 'editorGutter.modifiedBackground'],
 'untracked': ['gitDecoration.untrackedResourceForeground'], 'ansi_magenta': ['terminal.ansiMagenta'], 'ansi_cyan': ['terminal.ansiCyan'],
}
HARD_DEFAULTS = {'error': '#ff5c5c', 'warning': '#e6c12e', 'info': '#5c97e6', 'success': '#76cc52'}

def first_color(colors, keys):
    for k in keys:
        c = norm_hex(colors.get(k))
        if c: return c
    return None

def infer(old):
    """-> (palette dict, notes list, conflicts list)"""
    ot = OldTheme(old); colors = old.get('colors', {}); notes, conflicts, vals = [], [], {}
    # --- UI
    for role, keys in UI_PROBES.items():
        c = first_color(colors, keys)
        if role == 'ui_bg_hover': continue
        if c: vals[role] = rgb6(c)
    bg = vals.get('ui_bg')
    if not bg: sys.exit('theme has no editor.background')
    hc = first_color(colors, ['list.hoverBackground', 'editor.lineHighlightBackground', 'tab.hoverBackground'])
    if hc:
        if alpha_of(hc) < 255: vals['ui_bg_hover'] = rgb6(hc)
        else: vals['ui_bg_hover'] = B.r2h([min(255, max(0, b + 2 * (c - b))) for b, c in zip(B.h2r(bg), B.h2r(hc))])
    for r_, d in HARD_DEFAULTS.items():
        if r_ not in vals: vals[r_] = d; notes.append(f'{r_} not defined in the old theme; used default {d}')
    if 'ui_fg' not in vals: vals['ui_fg'] = '#d4d4d4'; notes.append('no foreground color found; used #d4d4d4')
    if 'ui_accent' not in vals: vals['ui_accent'] = vals['ui_fg']; notes.append('no accent found; used ui_fg')
    # --- syntax probes
    for role, probes in PROBES.items():
        hits = []
        for p in probes:
            r = ot.resolve(p.split())
            if r: hits.append((r[0], r[1], r[2], p))
        if not hits: continue
        top = max((h[0], h[1]) for h in hits)
        win = next(h for h in hits if (h[0], h[1]) == top)
        vals[role] = win[2]
        explicit = {h[2] for h in hits if h[0] >= 2}
        if len(explicit) > 1 and max(B.delta_e(a, b) for a in explicit for b in explicit) > 8:
            conflicts.append(f"{role}: probes disagree {', '.join(f'{h[3]}={h[2]}' for h in hits if h[0] >= 2)} -> kept {win[2]}")
    if 'variable' not in vals:
        ec = norm_hex(colors.get('editor.foreground')) or vals['ui_fg']; vals['variable'] = rgb6(ec)
    for req in ('keyword', 'function', 'string', 'number', 'type', 'comment'):
        if req not in vals: sys.exit(f'could not infer required role {req!r}')
    # --- brackets
    for i in range(1, 7):
        c = norm_hex(colors.get(f'editorBracketHighlight.foreground{i}'))
        if c: vals[f'bracket_{i}'] = rgb6(c)
    # --- json key levels
    levels = {}
    for i, anc, leaf, fg in ot.rules:
        if leaf == 'support.type.property-name.json' and anc and anc[0] == 'source.json':
            levels[anc.count('meta.structure.dictionary.value.json')] = fg
    json_levels = []
    if len(levels) > 1 or (levels and len(set(levels.values())) > 1):
        for n in range(max(levels) + 1): json_levels.append(levels.get(n, json_levels[-1] if json_levels else vals.get('data_key', vals['variable'])))
        vals['data_key'] = json_levels[0]
        if len(set(json_levels)) == 1: json_levels = []
    # --- prune roles equal to what they would inherit
    depth = {}
    def dep(k):
        if k in depth: return depth[k]
        fb = B.ROLE_BY_KEY[k]['fb']
        refs = [] if fb is None else [fb] if isinstance(fb, str) else [x for x in fb[1:3] if isinstance(x, str)]
        depth[k] = 1 + max([dep(x) for x in refs], default=-1); return depth[k]
    for k in B.ROLE_BY_KEY: dep(k)
    typ = old.get('type', 'dark')
    for k in sorted(vals, key=lambda k: depth[k]):
        if B.ROLE_BY_KEY[k]['fb'] is None: continue
        tmp = {a: b for a, b in vals.items() if a != k}
        inherited = B.Palette({'type': typ, 'colors': tmp})(k)
        if B.delta_e(inherited, vals[k]) < 3: del vals[k]
    # --- carry extras the kit does not derive
    P0 = B.Palette({'type': typ, 'colors': vals})
    kit_keys = set(B.build_ui(P0))
    ui_over = {k: v.lower() for k, v in colors.items() if k not in kit_keys and norm_hex(v)}
    sem_over = {}
    for k, v in (old.get('semanticTokenColors') or {}).items():
        c = norm_hex(v if isinstance(v, str) else (v or {}).get('foreground'))
        if not c: continue
        tgt = B.SEMANTIC.get(k)
        if tgt is None or B.delta_e(rgb6(c), P0(tgt)) > 8: sem_over[k] = rgb6(c)
    ordered = {k: None for k in B.REQUIRED}; ordered.update({r['key']: None for r in B.ROLES})
    ordered.update(vals)
    pal = {'name': old.get('name', 'theme'), 'type': typ, 'colors': ordered}
    if json_levels: pal['json_key_levels'] = json_levels
    if ui_over: pal['ui_overrides'] = ui_over
    if sem_over: pal['semantic_overrides'] = sem_over
    return pal, notes, conflicts, ot

# ───────────── comparison ─────────────
def ui_diffs(old_colors, new_colors, skip):
    out = []
    for k, v in old_colors.items():
        ov, nv = norm_hex(v), norm_hex(new_colors.get(k)); 
        if not ov or not nv or k in skip: continue
        d = B.delta_e(rgb6(ov), rgb6(nv)); da = abs(alpha_of(ov) - alpha_of(nv))
        out.append((d + (da / 8 if da > 24 else 0), k, ov, nv))
    return sorted(out, reverse=True)

def syntax_diffs(ot_old, ot_new):
    probes = set()
    for ot in (ot_old, ot_new):
        for i, anc, leaf, fg in ot.rules: probes.add(' '.join(anc + [leaf]))
    res = []
    for p in sorted(probes):
        a, b = ot_old.resolve(p.split()), ot_new.resolve(p.split())
        if a and b: res.append((B.delta_e(a[2], b[2]), p, a[2], b[2]))
        elif a and not b: res.append((99, p, a[2], 'none'))
    return sorted(res, reverse=True), len(probes)

# ───────────── overview image ─────────────
def overview(items, path):
    from PIL import Image, ImageDraw, ImageFont
    fp = next((p for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', '/System/Library/Fonts/Menlo.ttc'] if os.path.exists(p)), None)
    f = ImageFont.truetype(fp, 13) if fp else ImageFont.load_default()
    roles = ['keyword', 'keyword_special', 'function', 'type', 'string', 'number', 'constant', 'parameter', 'operator', 'comment', 'annotation', 'tag']
    rh, W = 54, 1180
    im = Image.new('RGB', (W, rh * len(items) + 10), '#101010'); d = ImageDraw.Draw(im)
    for n, (name, P) in enumerate(items):
        y = 5 + n * rh; d.rectangle((6, y, W - 6, y + rh - 4), fill=P('ui_bg'))
        d.text((16, y + 6), name[:30], font=f, fill=P('ui_fg')); d.text((16, y + 26), f"bg {P('ui_bg')}  accent {P('ui_accent')}", font=f, fill=P('ui_fg_muted'))
        for i, r in enumerate(roles):
            x = 300 + i * 72; d.rectangle((x, y + 8, x + 60, y + 28), fill=P(r)); d.text((x, y + 31), r[:9], font=ImageFont.truetype(fp, 10) if fp else f, fill=P('ui_fg_muted'))
    im.save(path)

# ───────────── main ─────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('themes', nargs='+'); ap.add_argument('-o', '--out', required=True); ap.add_argument('--no-preview', action='store_true')
    a = ap.parse_args()
    for sub in ('palettes', 'themes', 'previews'): os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    summary, sections, over_items = [], [], []
    for path in a.themes:
        stem = os.path.splitext(os.path.basename(path))[0]
        old = json.load(open(path, encoding='utf-8'))
        pal, notes, conflicts, ot_old = infer(old)
        json.dump(pal, open(os.path.join(a.out, 'palettes', stem + '.palette.json'), 'w'), indent=2); open(os.path.join(a.out, 'palettes', stem + '.palette.json'), 'a').write('\n')
        P = B.Palette(pal); new = B.build_theme(P)
        json.dump(new, open(os.path.join(a.out, 'themes', stem + '.json'), 'w'), indent=2, ensure_ascii=False); open(os.path.join(a.out, 'themes', stem + '.json'), 'a').write('\n')
        if not a.no_preview: B.render_preview(P, os.path.join(a.out, 'previews', stem + '.png'))
        over_items.append((pal['name'], P))
        ot_new = OldTheme(new); sd, nprobe = syntax_diffs(ot_old, ot_new); good = sum(1 for d in sd if d[0] <= 12)
        fid = 100 * (nprobe - sum(1 for d in sd if d[0] > 12)) / max(nprobe, 1)
        ud = ui_diffs(old.get('colors', {}), new['colors'], set(P.ui_overrides)); ubig = [u for u in ud if u[0] > 12]
        warns = [l.strip() for l in B.report(P) if 'low contrast' in l or 'too similar' in l]
        hue = next(l.split(':')[1].strip() for l in B.report(P) if 'hue families' in l)
        summary.append((stem, old.get('name'), P('ui_bg'), len(P.vals), len(P.inherited), hue, len(warns), len(P.ui_overrides), f'{fid:.0f}%', len(ud) - len(ubig), len(ud), len(ot_old.styled)))
        S = [f'## {old.get("name")}  (`{stem}.json`)', '']
        S.append(f'- {len(P.vals)} roles filled, {len(P.inherited)} inherited; {hue} hue families; background `{P("ui_bg")}`')
        S.append(f'- syntax fidelity {fid:.0f}% of {nprobe} probed scopes within dE 12; UI keys within dE 12: {len(ud) - len(ubig)}/{len(ud)}')
        if P.ui_overrides: S.append(f'- carried {len(P.ui_overrides)} extra UI keys as `ui_overrides`' + (f' and {len(P.semantic_overrides)} `semantic_overrides`' if P.semantic_overrides else ''))
        elif P.semantic_overrides: S.append(f'- carried {len(P.semantic_overrides)} `semantic_overrides`')
        if pal.get('json_key_levels'): S.append(f'- JSON key depth coloring: {len(pal["json_key_levels"])} levels')
        for n_ in notes: S.append(f'- note: {n_}')
        if ot_old.styled: S.append('- font styles removed (template allows italic on comments only): ' + '; '.join(f'{n[:28]} [{s}]' for n, s in ot_old.styled))
        if warns:
            S += ['', '**Checker warnings**'] + [f'- {w}' for w in warns]
        if conflicts:
            S += ['', '**Roles where the old theme colored related scopes differently (merged into one role)**'] + [f'- {c}' for c in conflicts]
        if [d for d in sd if d[0] > 12]:
            S += ['', '**Largest syntax differences vs the old theme**', '', '| scope | old | new |', '|---|---|---|']
            for d in [d for d in sd if d[0] > 12][:7]: S.append(f'| `{d[1][:70]}` | `{d[2]}` | `{d[3]}` |')
        if ubig:
            S += ['', '**Largest UI differences (derived instead of hand-set)**', '', '| key | old | new |', '|---|---|---|']
            for d in ubig[:5]: S.append(f'| `{d[1]}` | `{d[2]}` | `{d[3]}` |')
        sections.append('\n'.join(S))
        print(f'{stem}: roles {len(P.vals)}/{len(B.ROLES)}  hue={hue}  warn={len(warns)}  extras={len(P.ui_overrides)}  syntax-fidelity={fid:.0f}%')
    hdr = ['# Normalization report', '', f'{len(summary)} themes rebuilt from role palettes via `build_theme.py`.', '',
           '| theme | bg | roles set | inherited | hue fams | warnings | UI extras kept | syntax fidelity | UI keys close | styles dropped |', '|---|---|---|---|---|---|---|---|---|---|']
    for s in summary: hdr.append(f'| {s[1]} | `{s[2]}` | {s[3]} | {s[4]} | {s[5]} | {s[6]} | {s[7]} | {s[8]} | {s[9]}/{s[10]} | {s[11]} |')
    open(os.path.join(a.out, 'REPORT.md'), 'w').write('\n'.join(hdr) + '\n\n' + '\n\n'.join(sections) + '\n')
    overview(over_items, os.path.join(a.out, 'overview.png'))

if __name__ == '__main__': main()
