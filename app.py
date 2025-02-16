import streamlit as st
import py3Dmol
import math

# -------------------------------
# 基本工具與函式定義
# -------------------------------
def norm(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def dot_product(v1, v2):
    return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]

def normalize(v):
    n = norm(v)
    if n == 0:
        return (0,0,0)
    return (v[0]/n, v[1]/n, v[2]/n)

def add_axes(view, axis_length=3.0):
    """在視圖中加入 X (紅)、Y (綠)、Z (藍) 座標軸（加粗）"""
    radius = 0.05
    view.addCylinder({
        'start': {'x': -axis_length, 'y': 0, 'z': 0},
        'end':   {'x': axis_length, 'y': 0, 'z': 0},
        'radius': radius, 'color': 'red'
    })
    view.addCylinder({
        'start': {'x': 0, 'y': -axis_length, 'z': 0},
        'end':   {'x': 0, 'y': axis_length, 'z': 0},
        'radius': radius, 'color': 'green'
    })
    view.addCylinder({
        'start': {'x': 0, 'y': 0, 'z': -axis_length},
        'end':   {'x': 0, 'y': 0, 'z': axis_length},
        'radius': radius, 'color': 'blue'
    })

def teardrop_radius_modified(t, A=0.8, t0=0.8):
    """
    計算水滴連接處的半徑：
      - t∈[0,1]：t=0 與 t=1 時半徑均為 0
      - t<=t0 時用 A*sin(π*t/(2*t0))
      - t>t0 時用線性下降 A*(1-t)/(1-t0)
    """
    if t <= t0:
        return A * math.sin(math.pi * t / (2*t0))
    else:
        return A * (1-t) / (1-t0)

def perpendicular_vector(v):
    """
    給定向量 v，返回一個與 v 垂直的單位向量，
    若 v 接近零，則回傳 (1,0,0)。
    """
    vx, vy, vz = v
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return (1,0,0)
    else:
        perp = (-vy, vx, 0)
        n_val = norm(perp)
        return (perp[0]/n_val, perp[1]/n_val, perp[2]/n_val)

def add_teardrop_lobe(view, x, y, z, color='lightblue', steps=20, include_ligand=True):
    """
    沿著從中心 (0,0,0) 到 (x,y,z) 的方向，畫出水滴連接：
      - 利用多個小球模擬水滴，opacity = 0.6
      - 若為鍵結對 (include_ligand=True)，在 t=1 處畫出外部原子（半徑0.5）
      - 若為孤對 (include_ligand=False)，則不畫最邊邊的圓球，而在 t=0.5 處加上兩個小黑點代表電子對
    """
    for i in range(1, steps):
        t = i / steps
        cx, cy, cz = t * x, t * y, t * z
        r = teardrop_radius_modified(t, A=0.8, t0=0.8)
        view.addSphere({
            'center': {'x': cx, 'y': cy, 'z': cz},
            'radius': r,
            'color': color,
            'opacity': 0.6
        })
    if include_ligand:
        ligand_radius = 0.5
        view.addSphere({
            'center': {'x': x, 'y': y, 'z': z},
            'radius': ligand_radius,
            'color': color,
            'opacity': 0.9
        })
    else:
        t_electron = 0.5
        ex, ey, ez = t_electron * x, t_electron * y, t_electron * z
        p = perpendicular_vector((x, y, z))
        offset = 0.1
        sphere1_center = (ex + offset * p[0], ey + offset * p[1], ez + offset * p[2])
        sphere2_center = (ex - offset * p[0], ey - offset * p[1], ez - offset * p[2])
        view.addSphere({
            'center': {'x': sphere1_center[0], 'y': sphere1_center[1], 'z': sphere1_center[2]},
            'radius': 0.1, 'color': 'black', 'opacity': 1.0
        })
        view.addSphere({
            'center': {'x': sphere2_center[0], 'y': sphere2_center[1], 'z': sphere2_center[2]},
            'radius': 0.1, 'color': 'black', 'opacity': 1.0
        })

def add_arc_between(view, v1, v2, segments=20, allow_180_label=False):
    """
    在從 v1 到 v2 的圓球面上繪製一段圓弧（以小圓柱連接分段點），
    並在圓弧中點旁標示夾角（度數）。
    若 v1 與 v2 夾角為180°則特殊處理，使圓弧稍向外凸出。
    只有在 allow_180_label 為 True 或角度非180°時，才加入標籤。
    """
    u1 = normalize(v1)
    u2 = normalize(v2)
    r1 = norm(v1)
    r2 = norm(v2)
    r = ((r1 + r2) / 2.0) * 1.1
    dp = dot_product(u1, u2)
    if abs(dp + 1.0) < 1e-6:
        angle = math.pi
        n_vec = perpendicular_vector(u1)
    else:
        dp = max(-1.0, min(1.0, dp))
        angle = math.acos(dp)
        temp = (u2[0] - dp*u1[0], u2[1] - dp*u1[1], u2[2] - dp*u1[2])
        n_vec = normalize(temp)
    arc_points = []
    for i in range(segments + 1):
        phi = (i / segments) * angle
        point = (
            r * (u1[0] * math.cos(phi) + n_vec[0] * math.sin(phi)),
            r * (u1[1] * math.cos(phi) + n_vec[1] * math.sin(phi)),
            r * (u1[2] * math.cos(phi) + n_vec[2] * math.sin(phi))
        )
        arc_points.append(point)
    for i in range(len(arc_points) - 1):
        p_start = arc_points[i]
        p_end = arc_points[i + 1]
        view.addCylinder({
            'start': {'x': p_start[0], 'y': p_start[1], 'z': p_start[2]},
            'end':   {'x': p_end[0], 'y': p_end[1], 'z': p_end[2]},
            'radius': 0.02,
            'color': 'lightgray',
            'opacity': 0.5
        })
    mid_phi = angle / 2.0
    mid_point = (
        r * (u1[0] * math.cos(mid_phi) + n_vec[0] * math.sin(mid_phi)),
        r * (u1[1] * math.cos(mid_phi) + n_vec[1] * math.sin(mid_phi)),
        r * (u1[2] * math.cos(mid_phi) + n_vec[2] * math.sin(mid_phi))
    )
    angle_deg = math.degrees(angle)
    if not (abs(angle - math.pi) < 1e-6 and not allow_180_label):
        offset_vec = perpendicular_vector(mid_point)
        label_pos = (
            mid_point[0] + 0.15 * offset_vec[0],
            mid_point[1] + 0.15 * offset_vec[1],
            mid_point[2] + 0.15 * offset_vec[2]
        )
        view.addLabel(f"{angle_deg:.1f}°", {
            'position': {'x': label_pos[0], 'y': label_pos[1], 'z': label_pos[2]},
            'fontColor': 'black',
            'backgroundColor': 'transparent',
            'fontSize': 14,
            'showBackground': False
        })

def add_angle_labels(view, domains):
    n = len(domains)
    allow_180 = (n == 2)
    for i in range(n):
        for j in range(i + 1, n):
            if domains[i]['type'] == 'bond' and domains[j]['type'] == 'bond':
                add_arc_between(view, domains[i]['pos'], domains[j]['pos'], segments=30, allow_180_label=allow_180)

def show_vsepr_teardrop(domains, shape_name, show_angle_labels=True):
    """
    繪製 VSEPR 模型：
      - 中心原子以黑球 (半徑 0.5)
      - 每個電子域以水滴連接中心與外部原子呈現：
            鍵結對 (bond)：顏色為 lightblue，且在 t=1 處畫出外部原子
            孤對 (lp)：顏色為 pink，不畫 t=1 的外部圓球，而在中間標示兩個小黑點
      - 若所有電子域皆為鍵結對且 show_angle_labels 為 True，則加上夾角標示
      - 顯示座標軸
    """
    view = py3Dmol.view(width=600, height=600)
    add_axes(view, axis_length=3.0)
    view.addSphere({
        'center': {'x': 0, 'y': 0, 'z': 0},
        'radius': 0.5,
        'color': 'black',
        'opacity': 1.0
    })
    for d in domains:
        (x, y, z) = d['pos']
        if d['type'] == 'bond':
            col = 'lightblue'
            include_ligand = True
        else:
            col = 'pink'
            include_ligand = False
        add_teardrop_lobe(view, x, y, z, color=col, steps=20, include_ligand=include_ligand)
    if show_angle_labels and all(d['type'] == 'bond' for d in domains):
        add_angle_labels(view, domains)

    # 調整預設視角旋轉：
    ed_count = len(domains)
    if ed_count == 2:
        view.rotate(90, 'y')
    elif ed_count == 3:
        view.rotate(90, 'z')
    elif ed_count == 4:
        # 對於 4 電子域（正四面體），不做額外旋轉，保持預設指向正四面體四個角
        pass
    elif ed_count == 6:
        if any(keyword in shape_name for keyword in ["平面四方", "T-shaped", "T形"]):
            pass
        elif any(keyword in shape_name for keyword in ["直線"]):
            view.rotate(90, 'z')
        else:
            view.rotate(90, 'x')
    else:
        view.rotate(-90, 'x')

    view.zoomTo()
    # 返回產生的 HTML 字串供 Streamlit 嵌入
    return view._make_html()

# -------------------------------
# VSEPR 模型定義（2～6 電子域）
# -------------------------------
vsepr_geometries = {
    "2_0": {
        "shape_name": "2 電子域, 0 LP: Linear (直線)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "bond"},
            {"pos": (0, 0, -2.5), "type": "bond"}
        ]
    },
    "3_0": {
        "shape_name": "3 電子域, 0 LP: Trigonal Planar (平面三角)",
        "domains": [
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-1.25, 2.165, 0), "type": "bond"},
            {"pos": (-1.25, -2.165, 0), "type": "bond"}
        ]
    },
    "3_1": {
        "shape_name": "3 電子域, 1 LP: Bent (角形)",
        "domains": [
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-1.25, 2.165, 0), "type": "bond"},
            {"pos": (-1.25, -2.165, 0), "type": "lp"}
        ]
    },
    "4_0": {
        "shape_name": "4 電子域, 0 LP: Tetrahedral (四面體)",
        "domains": [
            {"pos": (2.357, 0, -0.8333), "type": "bond"},
            {"pos": (-1.1785, 2.0413, -0.8333), "type": "bond"},
            {"pos": (-1.1785, -2.0413, -0.8333), "type": "bond"},
            {"pos": (0, 0, 2.5), "type": "bond"}
        ]
    },
    "4_1": {
        "shape_name": "4 電子域, 1 LP: Trigonal Pyramidal (三角錐)",
        "domains": [
            {"pos": (2.357, 0, -0.8333), "type": "bond"},
            {"pos": (-1.1785, 2.0413, -0.8333), "type": "bond"},
            {"pos": (-1.1785, -2.0413, -0.8333), "type": "bond"},
            {"pos": (0, 0, 2.5), "type": "lp"}
        ]
    },
    "4_2": {
        "shape_name": "4 電子域, 2 LP: Bent (角形)",
        "domains": [
            {"pos": (2.357, 0, -0.8333), "type": "bond"},
            {"pos": (-1.1785, 2.0413, -0.8333), "type": "lp"},
            {"pos": (-1.1785, -2.0413, -0.8333), "type": "lp"},
            {"pos": (0, 0, 2.5), "type": "bond"}
        ]
    },
    "5_0": {
        "shape_name": "5 電子域, 0 LP: Trigonal Bipyramidal (三角雙錐)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "bond"},
            {"pos": (0, 0, -2.5), "type": "bond"},
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-1.25, 2.165, 0), "type": "bond"},
            {"pos": (-1.25, -2.165, 0), "type": "bond"}
        ]
    },
    "5_1": {
        "shape_name": "5 電子域, 1 LP: Seesaw (鞦韆形)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "bond"},
            {"pos": (0, 0, -2.5), "type": "bond"},
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-1.25, 2.165, 0), "type": "bond"},
            {"pos": (-1.25, -2.165, 0), "type": "lp"}
        ]
    },
    "5_2": {
        "shape_name": "5 電子域, 2 LP: T-shaped (T形)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "bond"},
            {"pos": (0, 0, -2.5), "type": "bond"},
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-1.25, 2.165, 0), "type": "lp"},
            {"pos": (-1.25, -2.165, 0), "type": "lp"}
        ]
    },
    "5_3": {
        "shape_name": "5 電子域, 3 LP: Linear (直線)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "bond"},
            {"pos": (0, 0, -2.5), "type": "bond"},
            {"pos": (2.5, 0, 0), "type": "lp"},
            {"pos": (-1.25, 2.165, 0), "type": "lp"},
            {"pos": (-1.25, -2.165, 0), "type": "lp"}
        ]
    },
    "6_0": {
        "shape_name": "6 電子域, 0 LP: Octahedral (八面體)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "bond"},
            {"pos": (0, 0, -2.5), "type": "bond"},
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-2.5, 0, 0), "type": "bond"},
            {"pos": (0, 2.5, 0), "type": "bond"},
            {"pos": (0, -2.5, 0), "type": "bond"}
        ]
    },
    "6_1": {
        "shape_name": "6 電子域, 1 LP: Square Pyramidal (四角錐)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "lp"},
            {"pos": (0, 0, -2.5), "type": "bond"},
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-2.5, 0, 0), "type": "bond"},
            {"pos": (0, 2.5, 0), "type": "bond"},
            {"pos": (0, -2.5, 0), "type": "bond"}
        ]
    },
    "6_2": {
        "shape_name": "6 電子域, 2 LP: Square Planar (平面四方)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "lp"},
            {"pos": (0, 0, -2.5), "type": "lp"},
            {"pos": (2.5, 0, 0), "type": "bond"},
            {"pos": (-2.5, 0, 0), "type": "bond"},
            {"pos": (0, 2.5, 0), "type": "bond"},
            {"pos": (0, -2.5, 0), "type": "bond"}
        ]
    },
    "6_3": {
        "shape_name": "6 電子域, 3 LP: T-shaped (T形)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "lp"},
            {"pos": (0, 0, -2.5), "type": "lp"},
            {"pos": (2.5, 0, 0), "type": "lp"},
            {"pos": (-2.5, 0, 0), "type": "bond"},
            {"pos": (0, 2.5, 0), "type": "bond"},
            {"pos": (0, -2.5, 0), "type": "bond"}
        ]
    },
    "6_4": {
        "shape_name": "6 電子域, 4 LP: Linear (直線)",
        "domains": [
            {"pos": (0, 0, 2.5), "type": "lp"},
            {"pos": (0, 0, -2.5), "type": "lp"},
            {"pos": (2.5, 0, 0), "type": "lp"},
            {"pos": (-2.5, 0, 0), "type": "lp"},
            {"pos": (0, 2.5, 0), "type": "bond"},
            {"pos": (0, -2.5, 0), "type": "bond"}
        ]
    }
}

# -------------------------------
# Streamlit 主程式
# -------------------------------
st.title("VSEPR 模型互動視圖")
st.write("請在側邊欄選擇要查看的模型。")

# 側邊欄選擇模型
options = sorted(vsepr_geometries.keys())
selected_key = st.sidebar.selectbox("選擇模型", options)
data = vsepr_geometries[selected_key]

# 若所有電子域都是鍵結對，則提供顯示夾角的選項
if all(d['type'] == 'bond' for d in data["domains"]):
    show_angles = st.sidebar.checkbox("顯示夾角標示", value=True)
else:
    show_angles = False

# 產生互動視圖的 HTML 字串
html_str = show_vsepr_teardrop(data["domains"], data["shape_name"], show_angle_labels=show_angles)

# 顯示標題（僅顯示 shape_name，不附加額外標題文字）
st.header(data["shape_name"])

# 嵌入 py3Dmol 的 HTML 互動視圖
st.components.v1.html(html_str, width=800, height=800)
