"""Shading check for the 20 kW rooftop model rebuilt in SketchUp Free on 2026-10-09.

The geometry below is the same set of numbers the SketchUp model was built from (every part
was placed by typed coordinates and checked against SketchUp's own bounding boxes).
From 12 points on every module it fires a ray at the sun and records whether the
parapet, the coping, the stair room or another row is in the way.

Frame: house-local metres. X runs along the rows (true bearing 58 deg), Y runs along the
long side of the roof (true bearing 328 deg), Z is up from the ground. Modules face -Y,
which is true bearing 148 deg. Origin = outer corner of the walls at the south west / south east.

Run:  python -I shading_check.py   (plain Python 3, no packages)
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

LAT, LON, TZ = 33.68934, 72.99206, 5.0
AXIS_X_BEARING = 58.0          # true bearing of house-local +X
TILT = 20.0
MOD_W, MOD_L, MOD_T = 1.134, 1.99, 0.035
GAP = 0.02
ROWS, COLS = 6, 6
PITCH = 2.80
ROOF_Z = 6.56                  # top of the roof screed
FRONT_H = 0.30                 # front edge of the modules above the screed
ARRAY_X0, ARRAY_Y0 = 0.80, 0.915

# ---------------------------------------------------------------- obstacles
def box(x0, x1, y0, y1, z0, z1):
    return (x0, x1, y0, y1, z0, z1)

BOXES = [
    # parapet ring, 0.2 m thick, top at 7.46
    box(0.0, 11.7, 0.0, 0.2, 6.5, 7.46),
    box(0.0, 11.7, 17.5, 17.7, 6.5, 7.46),
    box(0.0, 0.2, 0.2, 17.5, 6.5, 7.46),
    box(11.5, 11.7, 0.2, 17.5, 6.5, 7.46),
    # coping ring, 0.3 m wide, overhanging the parapet 0.05 m each side, top at 7.52
    box(-0.05, 11.75, -0.05, 0.25, 7.46, 7.52),
    box(-0.05, 11.75, 17.45, 17.75, 7.46, 7.52),
    box(-0.05, 0.25, 0.25, 17.45, 7.46, 7.52),
    box(11.45, 11.75, 0.25, 17.45, 7.46, 7.52),
    # stair room and its roof slab
    box(8.45, 10.95, 4.45, 6.95, 6.5, 9.26),
    box(8.35, 11.05, 4.35, 7.05, 9.26, 9.38),
]
BOX_NAMES = ["parapet"] * 4 + ["coping"] * 4 + ["stair room"] * 2

C20, S20 = math.cos(math.radians(TILT)), math.sin(math.radians(TILT))


def module_origin(r, c):
    """Front bottom corner of module (r, c) in house-local metres."""
    return (ARRAY_X0 + c * (MOD_W + GAP), ARRAY_Y0 + r * PITCH, ROOF_Z + FRONT_H)


def to_module(p, origin):
    """World point -> module frame (x across, s up the slope, n out of the top face)."""
    dx, dy, dz = p[0] - origin[0], p[1] - origin[1], p[2] - origin[2]
    return (dx, dy * C20 + dz * S20, -dy * S20 + dz * C20)


def dir_to_module(d):
    return (d[0], d[1] * C20 + d[2] * S20, -d[1] * S20 + d[2] * C20)


def from_module(q, origin):
    x, s, n = q
    return (origin[0] + x, origin[1] + s * C20 - n * S20, origin[2] + s * S20 + n * C20)


def slab_hit(o, d, lo, hi, eps=1e-9):
    """Ray o + t d, t > 1e-6, against an axis-aligned box lo..hi. Returns True on a hit."""
    tmin, tmax = 1e-6, 1e9
    for a in range(3):
        if abs(d[a]) < eps:
            if o[a] < lo[a] or o[a] > hi[a]:
                return False
        else:
            t1 = (lo[a] - o[a]) / d[a]
            t2 = (hi[a] - o[a]) / d[a]
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 > tmin:
                tmin = t1
            if t2 < tmax:
                tmax = t2
            if tmin > tmax:
                return False
    return True


MODULES = [(r, c) for r in range(ROWS) for c in range(COLS)]
ORIGINS = {m: module_origin(*m) for m in MODULES}
MOD_LO, MOD_HI = (0.0, 0.0, 0.0), (MOD_W, MOD_L, MOD_T)

US = [1 / 6, 3 / 6, 5 / 6]
VS = [(k + 0.5) / 10 for k in range(10)]   # 10 equal strips up the slope
POINTS = []   # (module, world point)
for m in MODULES:
    for u in US:
        for v in VS:
            POINTS.append((m, from_module((u * MOD_W, v * MOD_L, MOD_T + 0.001), ORIGINS[m])))


def slab_t(o, d, lo, hi, eps=1e-9):
    """Entry distance of ray o + t d into the box lo..hi, or None."""
    tmin, tmax = 1e-6, 1e9
    for a in range(3):
        if abs(d[a]) < eps:
            if o[a] < lo[a] or o[a] > hi[a]:
                return None
        else:
            t1 = (lo[a] - o[a]) / d[a]
            t2 = (hi[a] - o[a]) / d[a]
            if t1 > t2:
                t1, t2 = t2, t1
            tmin = max(tmin, t1)
            tmax = min(tmax, t2)
            if tmin > tmax:
                return None
    return tmin


def is_shaded(p, own, d):
    for b in BOXES:
        if slab_hit(p, d, b[0::2], b[1::2]):
            return True
    dm = dir_to_module(d)
    for m in MODULES:
        if m != own and slab_hit(to_module(p, ORIGINS[m]), dm, MOD_LO, MOD_HI):
            return True
    return False


def blocker(p, own, d):
    """What the ray from p towards the sun hits first, or None if it reaches the sun.
    The module frame is a rotation plus a shift, so distances along the ray are the same in both frames."""
    if not is_shaded(p, own, d):
        return None
    best, name = 1e18, None
    for b, nm in zip(BOXES, BOX_NAMES):
        t = slab_t(p, d, b[0::2], b[1::2])
        if t is not None and t < best:
            best, name = t, nm
    dm = dir_to_module(d)
    for m in MODULES:
        if m == own:
            continue
        t = slab_t(to_module(p, ORIGINS[m]), dm, MOD_LO, MOD_HI)
        if t is not None and t < best:
            best = t
            name = "row in front" if m[0] < own[0] else ("same row" if m[0] == own[0] else "row behind")
    return name

# ---------------------------------------------------------------- sun position (NOAA)
def julian_day(y, mo, d, hour_ut):
    if mo <= 2:
        y -= 1
        mo += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + d + b - 1524.5 + hour_ut / 24.0


def sun_position(y, mo, d, local_hour):
    """Returns (elevation deg, azimuth deg clockwise from true north), no refraction."""
    jd = julian_day(y, mo, d, local_hour - TZ)
    jc = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    M = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    Mr = math.radians(M)
    C = (math.sin(Mr) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
         + math.sin(2 * Mr) * (0.019993 - 0.000101 * jc) + math.sin(3 * Mr) * 0.000289)
    true_long = L0 + C
    omega = 125.04 - 1934.136 * jc
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    mean_obliq = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliq = mean_obliq + 0.00256 * math.cos(math.radians(omega))
    decl = math.asin(math.sin(math.radians(obliq)) * math.sin(math.radians(app_long)))
    yv = math.tan(math.radians(obliq / 2)) ** 2
    L0r = math.radians(L0)
    eqt = 4 * math.degrees(yv * math.sin(2 * L0r) - 2 * e * math.sin(Mr)
                           + 4 * e * yv * math.sin(Mr) * math.cos(2 * L0r)
                           - 0.5 * yv * yv * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    tst = (local_hour * 60 + eqt + 4 * LON - 60 * TZ) % 1440
    ha = tst / 4 - 180
    lat = math.radians(LAT)
    har = math.radians(ha)
    cz = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(har)
    cz = max(-1.0, min(1.0, cz))
    zen = math.acos(cz)
    el = 90 - math.degrees(zen)
    den = math.cos(lat) * math.sin(zen)
    if abs(den) < 1e-12:
        az = 180.0
    else:
        ca = (math.sin(lat) * math.cos(zen) - math.sin(decl)) / den
        ca = max(-1.0, min(1.0, ca))
        acd = math.degrees(math.acos(ca))
        az = (acd + 180) % 360 if ha > 0 else (540 - acd) % 360
    return el, az


def sun_vector(el, az):
    """Unit vector towards the sun in house-local axes."""
    ce = math.cos(math.radians(el))
    return (ce * math.cos(math.radians(az - AXIS_X_BEARING)),
            ce * math.cos(math.radians(az - (AXIS_X_BEARING - 90))),
            math.sin(math.radians(el)))


# module plane normal in house-local axes (faces -Y, tilted 20 deg up)
NORMAL = (0.0, -S20, C20)


def clear_sky_beam(el):
    """Direct normal irradiance, W/m2, Meinel clear-sky model with Kasten-Young air mass."""
    if el <= 0:
        return 0.0
    am = 1 / (math.sin(math.radians(el)) + 0.50572 * (el + 6.07995) ** -1.6364)
    return 1353 * 0.7 ** (am ** 0.678)

# ---------------------------------------------------------------- studies
def study_four_dates():
    dates = [("21 Mar", 3, 21), ("21 Jun", 6, 21), ("21 Sep", 9, 21), ("21 Dec", 12, 21)]
    lit = {m: 0 for m in MODULES}
    tot = {m: 0 for m in MODULES}
    by_hour = []
    skipped = []
    for label, mo, d in dates:
        for h in range(6, 19):
            el, az = sun_position(2026, mo, d, h)
            if el <= 5:
                continue
            sv = sun_vector(el, az)
            if sum(a * b for a, b in zip(sv, NORMAL)) <= 0:
                skipped.append(f"{label} {h:02d}:00")
                continue          # sun behind the module plane: no direct beam on the fronts
            n_sh = 0
            causes = {}
            for m, p in POINTS:
                tot[m] += 1
                who = blocker(p, m, sv)
                if who is None:
                    lit[m] += 1
                else:
                    n_sh += 1
                    causes[who] = causes.get(who, 0) + 1
            by_hour.append({"date": label, "hour": f"{h:02d}:00", "sun_elevation_deg": round(el, 1),
                            "sun_azimuth_deg": round(az, 1),
                            "sample_points_in_sun_pct": round(100 * (1 - n_sh / len(POINTS)), 1),
                            "shaded_by": "; ".join(f"{k} {v}" for k, v in sorted(causes.items()))})
    access = {m: lit[m] / tot[m] for m in MODULES}
    return access, by_hour, tot[MODULES[0]] // (len(US) * len(VS)), skipped


def study_annual(day_step=7, minute_step=15):
    """Clear-sky direct beam on the module plane, the share lost to shading, per module."""
    total = {m: 0.0 for m in MODULES}
    lost = {m: 0.0 for m in MODULES}
    cause_loss = {}
    import datetime
    day = datetime.date(2026, 1, 1)
    end = datetime.date(2026, 12, 31)
    while day <= end:
        t = 5 * 60
        while t <= 20 * 60:
            el, az = sun_position(day.year, day.month, day.day, t / 60)
            if el > 0:
                sv = sun_vector(el, az)
                cosi = sum(a * b for a, b in zip(sv, NORMAL))
                if cosi > 0:
                    beam = clear_sky_beam(el) * cosi
                    for m, p in POINTS:
                        total[m] += beam
                        who = blocker(p, m, sv)
                        if who is not None:
                            lost[m] += beam
                            cause_loss[who] = cause_loss.get(who, 0.0) + beam
            t += minute_step
        day += datetime.timedelta(days=day_step)
    all_total = sum(total.values())
    return ({m: lost[m] / total[m] for m in MODULES}, sum(lost.values()) / all_total,
            {k: v / all_total for k, v in cause_loss.items()})


def edge_reach(el, az):
    """For long parallel rows: how far up the next row's top face the shadow of a row's rear top edge
    climbs, in metres along the module from its low edge (0 = clear). Exact in the Y-Z plane."""
    sv = sun_vector(el, az)
    if sv[1] >= 0 or el <= 0:
        return 0.0                       # sun behind the rows' facing: no forward shading
    tan_prof = sv[2] / -sv[1]            # profile angle in the Y-Z plane
    rear = from_module((0.0, MOD_L, MOD_T), (0.0, 0.0, 0.0))
    # shadow line from the rear top edge: z = rear_z - tan_prof * (y - rear_y)
    # next row's top face: y = PITCH + s cos20 - MOD_T sin20, z = s sin20 + MOD_T cos20
    a = rear[2] + tan_prof * rear[1] - tan_prof * (PITCH - MOD_T * S20) - MOD_T * C20
    s = a / (S20 + tan_prof * C20)
    return max(0.0, min(MOD_L, s))


def inter_row_window_dec21():
    """Clock times on 21 December, 5 minute steps, when no row's shadow reaches the row behind."""
    free = []
    for i in range(0, 24 * 60, 5):
        h = i / 60
        el, az = sun_position(2026, 12, 21, h)
        if el <= 0:
            continue
        free.append((h, edge_reach(el, az) <= 0.0, el, az))
    return free


def blocker_rows_only(p, own, d):
    dm = dir_to_module(d)
    for m in MODULES:
        if m[0] == own[0]:
            continue
        if slab_hit(to_module(p, ORIGINS[m]), dm, MOD_LO, MOD_HI):
            return True
    return False


def noon_margin_dec21():
    """Gap left between a row's shadow and the next row at 12:00 on 21 December, metres,
    measured along the roof at right angles to the rows."""
    el, az = sun_position(2026, 12, 21, 12.0)
    sv = sun_vector(el, az)
    rear_top = from_module((0.0, MOD_L, MOD_T), (0.0, 0.0, 0.0))     # row frame, origin at front bottom
    next_front_top = (0.0, PITCH + from_module((0, 0, MOD_T), (0, 0, 0))[1], from_module((0, 0, MOD_T), (0, 0, 0))[2])
    drop = rear_top[2] - next_front_top[2]
    # horizontal travel of the shadow per metre of drop, projected on the row normal (-Y)
    horiz = drop / math.tan(math.radians(el))
    along_normal = horiz * (sv[1] / math.hypot(sv[0], sv[1])) * -1
    gap = next_front_top[1] - rear_top[1]
    return el, az, along_normal, gap


def main():
    access, by_hour, n_sun, skipped = study_four_dates()
    arr = sum(access.values()) / len(access)
    worst = min(access, key=access.get)
    best = max(access, key=access.get)
    with open(os.path.join(HERE, "solar-access-by-module.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row (1 = front, south east)", "module (1 = south west end)", "solar access %"])
        for r, c in MODULES:
            w.writerow([r + 1, c + 1, round(100 * access[(r, c)], 1)])
    with open(os.path.join(HERE, "array-in-sun-by-hour.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(by_hour[0].keys()))
        w.writeheader()
        w.writerows(by_hour)

    loss_by_mod, loss_all, cause = study_annual()
    with open(os.path.join(HERE, "annual-beam-loss-by-module.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "module", "clear-sky direct beam lost to shading %"])
        for r, c in MODULES:
            w.writerow([r + 1, c + 1, round(100 * loss_by_mod[(r, c)], 2)])

    win = inter_row_window_dec21()
    free_times = [h for h, ok, el, az in win if ok]
    strip = []
    for hh in (9, 10, 11, 11.5, 12):
        e2, a2 = sun_position(2026, 12, 21, hh)
        strip.append(f"{int(hh)}:{round(hh % 1 * 60):02d} {edge_reach(e2, a2):.2f} m")
    el, az, shadow, gap = noon_margin_dec21()

    lines = []
    lines.append(f"sample points: {len(POINTS)} ({len(MODULES)} modules x {len(US)} across x {len(VS)} up the slope)")
    lines.append(f"sun positions, four dates, hourly, elevation > 5 deg and in front of the modules: {n_sun}"
                 f" (left out, sun behind the modules: {', '.join(skipped) or 'none'})")
    lines.append(f"array solar access: {100 * arr:.1f}%")
    lines.append(f"worst module: row {worst[0] + 1}, module {worst[1] + 1}: {100 * access[worst]:.1f}%")
    lines.append(f"best module: row {best[0] + 1}, module {best[1] + 1}: {100 * access[best]:.1f}%")
    for row in by_hour:
        if row["date"] == "21 Dec":
            lines.append(f"  21 Dec {row['hour']}: sun {row['sun_elevation_deg']} deg up, az {row['sun_azimuth_deg']}, "
                         f"sample points in sun {row['sample_points_in_sun_pct']}%  [{row['shaded_by']}]")
    lines.append(f"annual clear-sky direct beam lost to shading (weekly, 15 min): {100 * loss_all:.2f}%")
    for k, v in sorted(cause.items(), key=lambda kv: -kv[1]):
        lines.append(f"  of which {k} (nearest object on the ray): {100 * v:.2f}%")
    wl = max(loss_by_mod, key=loss_by_mod.get)
    lines.append(f"worst module annual beam loss: row {wl[0] + 1}, module {wl[1] + 1}: {100 * loss_by_mod[wl]:.2f}%")
    if free_times:
        lines.append(f"21 Dec, no row's shadow reaches the row behind from {int(free_times[0])}:{round(free_times[0] % 1 * 60):02d} "
                     f"until sunset (last sun-up step {int(free_times[-1])}:{round(free_times[-1] % 1 * 60):02d}; exact edge geometry, 5 min steps)")
    lines.append("21 Dec, how far the row in front's shadow climbs up each module from its low edge: " + "; ".join(strip))
    lines.append(f"21 Dec 12:00: sun {el:.2f} deg up, az {az:.1f}; in plan, the shadow of a row's rear top edge reaches "
                 f"{shadow:.3f} m along +Y by the height of the next row's front top edge, against a gap of {gap:.3f} m: "
                 f"margin {gap - shadow:.3f} m")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(HERE, "shading-check-results.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
