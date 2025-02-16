import streamlit as st
import py3Dmol
import math

# 自訂 CSS：讓 radio 按鈕水平排列，並允許多行顯示
st.markdown(
    """
    <style>
    div[data-baseweb="radio"] > div {
      flex-direction: row;
      flex-wrap: wrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
        return (0, 0, 0)
    return (v[0]/n, v[1]/n, v[2]/n)

def add_axes(view, axis_length=3.0):
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
    if t <= t0:
        return A * math.sin(math.pi * t / (2*t0))
    else:
        return A * (1-t) / (1-t0)

def perpendicular_vector(v):
    vx, vy, vz = v
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return (1,0,0)
    else:
        perp = (-vy, vx, 0)
        n_val = norm(perp)
        return (perp[0]/n_val, perp[1]/n_val, perp[2]/n_val)

def add_teardrop_lobe(view, x, y, z, color='lightblue', steps=20, include_ligand=True):
    """繪製水滴狀的 lobe。若 include_ligand=True 則在末端畫出外部原子；否則視為孤對，畫出中間兩個小黑點。"""
    for i in range(1, steps):
        t = i/steps
        cx, cy, cz = t*x, t*y, t*z
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
        ex, ey, ez = t_electron*x, t_electron*y, t_electron*z
        p = perpendicular_vector((x, y, z))
        offset = 0.1
        sphere1_center = (ex + offset*p[0], ey + offset*p[1], ez + offset*p[2])
        sphere2_center = (ex - offset*p[0], ey - offset*p[1], ez - offset*p[2])
        view.addSphere({
            'center': {'x': sphere1_center[0], 'y': sphere1_center[1], 'z': sphere1_center[2]},
            'radius': 0.1, 'color': 'black', 'opacity': 1.0
        })
        view.addSphere({
            'center': {'x': sphere2_center[0], 'y': sphere2_center[1], 'z': sphere2_center[2]},
            'radius': 0.1, 'color': 'black', 'opacity': 1.0
        })

def add_arc_between(view, v1, v2, segments=20, allow_180_label=False):
    """在 v1 和 v2 之間繪製一段圓弧並標示角度。"""
    u1 = normalize(v1)
    u2 = normalize(v2)
    r1 = norm(v1)
    r2 = norm(v2)
    r = ((r1 + r2)/2.0)*1.1
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
    for i in range(segments+1):
        phi = (i/segments)*angle
        point = (
            r*(u1[0]*math.cos(phi) + n_vec[0]*math.sin(phi)),
            r*(u1[1]*math.cos(phi) + n_vec[1]*math.sin(phi)),
            r*(u1[2]*math.cos(phi) + n_vec[2]*math.sin(phi))
        )
        arc_points.append(point)
    for i in range(len(arc_points)-1):
        p_start = arc_points[i]
        p_end = arc_points[i+1]
        view.addCylinder({
            'start': {'x': p_start[0], 'y': p_start[1], 'z': p_start[2]},
            'end':   {'x': p_end[0], 'y': p_end[1], 'z': p_end[2]},
            'radius': 0.02,
            'color': 'lightgray',
            'opacity': 0.5
        })
    mid_phi = angle/2.0
    mid_point = (
        r*(u1[0]*math.cos(mid_phi) + n_vec[0]*math.sin(mid_phi)),
        r*(u1[1]*math.cos(mid_phi) + n_vec[1]*math.sin(mid_phi)),
        r*(u1[2]*math.cos(mid_phi) + n_vec[2]*math.sin(mid_phi))
    )
    angle_deg = math.degrees(angle)
    if not (abs(angle - math.pi) < 1e-6 and not allow_180_label):
        offset_vec = perpendicular_vector(mid_point)
        label_pos = (
            mid_point[0] + 0.15*offset_vec[0],
            mid_point[1] + 0.15*offset_vec[1],
            mid_point[2] + 0.15*offset_vec[2]
        )
        view.addLabel(f"{angle_deg:.1f}°", {
            'position': {'x': label_pos[0], 'y': label_pos[1], 'z': label_pos[2]},
            'fontColor': 'black',
            'backgroundColor': 'transparent',
            'fontSize': 14,
            'showBackground': False
        })

def add_angle_labels(view, domains):
    """若全部都是鍵結對，就為各對鍵繪製圓弧並標示角度。"""
    n = len(domains)
    allow_180 = (n == 2)
    for i in range(n):
        for j in range(i+1, n):
            if domains[i]['type'] == 'bond' and domains[j]['type'] == 'bond':
                add_arc_between(view, domains[i]['pos'], domains[j]['pos'], segments=30, allow_180_label=allow_180)

def show_vsepr_teardrop(domains, shape_name, show_angle_labels=True):
    """繪製 VSEPR 模型：4 電子域時改成理想正四面體；再將背景改成透明。"""
    if len(domains) == 4:
        R = 2.5
        s = R / math.sqrt(3)
        domains = [
            {"pos": ( s,  s,  s), "type": domains[0]["type"]},
            {"pos": ( s, -s, -s), "type": domains[1]["type"]},
            {"pos": (-s,  s, -s), "type": domains[2]["type"]},
            {"pos": (-s, -s,  s), "type": domains[3]["type"]}
        ]
    # py3Dmol 視圖：300×300
    view = py3Dmol.view(width=300, height=300)
    add_axes(view, axis_length=3.0)
    # 中心原子
    view.addSphere({
        'center': {'x': 0, 'y': 0, 'z': 0},
        'radius': 0.5,
        'color': 'black',
        'opacity': 1.0
    })
    # 繪製電子域
    for d in domains:
        (x, y, z) = d['pos']
        if d['type'] == 'bond':
            col = 'lightblue'
            include_ligand = True
        else:
            col = 'pink'
            include_ligand = False
        add_teardrop_lobe(view, x, y, z, color=col, steps=20, include_ligand=include_ligand)
    # 若全為鍵結對且 show_angle_labels=True，就加上夾角標示
    if show_angle_labels and all(d['type']=='bond' for d in domains):
        add_angle_labels(view, domains)

    # 預設旋轉
    ed_count = len(domains)
    if ed_count == 2:
        view.rotate(90, 'y')
    elif ed_count == 3:
        view.rotate(90, 'z')
    elif ed_count == 4:
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
    # 產生 HTML 並將背景替換為透明
    html_str = view._make_html()
    html_str = html_str.replace("background-color: white;", "background-color: transparent;")
    return html_str

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
    # ...省略，其餘 3~6 電子域與原先相同...
}

# -------------------------------
# Streamlit 主程式
# -------------------------------
st.title("VSEPR 模型互動視圖")

# 第一步：選擇電子域數（radio 水平排列）
domain_counts = sorted({ key.split('_')[0] for key in vsepr_geometries.keys() }, key=int)
selected_count = st.radio("選擇電子域數", domain_counts, horizontal=True)

# 第二步：從該電子域數的模型中選擇（radio 水平排列）
group_options = [key for key in sorted(vsepr_geometries.keys()) if key.startswith(selected_count)]
selected_key = st.radio("選擇模型", group_options, horizontal=True)

data = vsepr_geometries[selected_key]
# 若全部是鍵結對，就顯示是否要標示夾角
if all(d['type'] == 'bond' for d in data["domains"]):
    show_angles = st.checkbox("顯示夾角標示", value=True)
else:
    show_angles = False

html_str = show_vsepr_teardrop(data["domains"], data["shape_name"], show_angle_labels=show_angles)

# 顯示模型名稱
st.header(data["shape_name"])

# 外層容器：380×380 + padding=20，確保邊框完整
html_str_wrapped = f"<div style='border:2px solid #000; margin:10px; padding:20px; width:380px; height:380px; box-sizing:border-box;'>{html_str}</div>"

# 最終嵌入：寬高同 380×380
st.components.v1.html(html_str_wrapped, width=380, height=380)
