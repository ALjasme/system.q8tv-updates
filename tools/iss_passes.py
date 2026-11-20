"""Visible passes of the International Space Station over Kuwait City for the next 10 days -> iss.json.
A pass counts when the station is sunlit, the sky is dark enough (sun below -6°) and it climbs at least 25°.
Usage: python tools/iss_passes.py OUTPUT.json   (orbit from CelesTrak, ephemeris de421 from Skyfield)"""
import json, sys, datetime, urllib.request
from skyfield.api import load, wgs84, EarthSatellite
LAT, LON = 29.3759, 47.9774
DIRS = ["الشمال", "الشمال الشرقي", "الشرق", "الجنوب الشرقي", "الجنوب", "الجنوب الغربي", "الغرب", "الشمال الغربي"]
ts = load.timescale(); eph = load('de421.bsp')
req = urllib.request.Request("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle", headers={"User-Agent": "system.q8tv"})
lines = urllib.request.urlopen(req, timeout=30).read().decode().strip().splitlines()
sat = EarthSatellite(lines[1].strip(), lines[2].strip(), lines[0].strip(), ts)
home = wgs84.latlon(LAT, LON, 10)
t0 = ts.now(); t1 = ts.tt_jd(t0.tt + 10)  # orbits drift; 10 days keeps times within about a minute
t, ev = sat.find_events(home, t0, t1, altitude_degrees=10.0)
def kw(x): return (x + 3 / 24).utc_strftime('%Y-%m-%dT%H:%M')
def side(x):
    az = (sat - home).at(x).altaz()[1].degrees
    return DIRS[int((az + 22.5) % 360 // 45)]
passes, cur = [], {}
for ti, e in zip(t, ev):
    if e == 0: cur = {"rise": ti}
    elif e == 1 and "rise" in cur: cur["max"] = ti
    elif e == 2 and "max" in cur:
        tm = cur["max"]; alt = (sat - home).at(tm).altaz()[0].degrees
        sun_alt = (eph['earth'] + home).at(tm).observe(eph['sun']).apparent().altaz()[0].degrees
        lit = sat.at(tm).is_sunlit(eph)
        if alt >= 25 and sun_alt < -6 and lit:
            passes.append({"start": kw(cur["rise"]), "max": kw(tm), "end": kw(ti), "alt": round(alt),
                           "from": side(cur["rise"]), "to": side(ti),
                           "minutes": max(1, round((ti.tt - cur["rise"].tt) * 1440))})
        cur = {}
json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), "passes": passes},
          open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(len(passes), "passes")
