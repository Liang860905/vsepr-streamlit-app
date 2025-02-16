import streamlit as st
import py3Dmol
import math
import base64

# 設定頁面配置與全局 CSS（置中、水平排列 radio）
st.set_page_config(page_title="VSEPR 模型", layout="centered")
st.markdown(
    """
    <style>
    /* 讓 radio 按鈕水平排列且置中 */
    div[data-baseweb="radio"] > div {
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: center;
    }
    .center-all {
      text-align: center;
      margin: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 將整個頁面內容包在一個置中的 div 裡
st.markdown("<div class='center-all'>", unsafe_allow_html=True)

# -------------------------------
# 工具函式
# -------------------------------
def norm(v):
    return math.sqrt(sum(i * i for i in v))

def dot_product(v1, v2):
    return sum(a * b for a, b in zip(v1, v2))

def normalize(v):
    n = norm(v)
    return tuple(i / n for i in v) if n else (0, 0, 0)

def add_axes(view, axis_length=3.0):
    colors = ['red', 'green', 'blue']
    starts = [(-axis_length, 0, 0), (0, -axis_length, 0), (0, 0, -axis_length)]
    ends   = [(axis_length, 0, 0), (0, axis_length, 0), (0, 0, axis_length)]
    for s, e, c in zip(starts, ends, colors):
        view.addCylinder({
            'start': {'x': s[0], 'y': s[1], 'z': s[2]},
            'end': {'x': e[0], 'y': e[1], 'z': e[2]},
            'radius': 0.05,
            'color': c
        })

def teardrop_radius_modified(t, A=0.8, t0=0.8):
    return A * math.sin(math.pi * t / (2*t0)) if t <= t0 else A * (1-t) / (1-t0)

def perpendicular_vector(v):
    vx, vy, vz = v
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return (1, 0, 0)
    perp = (-vy, vx, 0)
    n_val = norm(perp)
    return tuple(i / n_val for i in perp)

def add_teardrop_lobe(view, x, y, z, color='lightblue', steps=20, include_ligand=True):
    for i in range(1, steps):
        t = i / steps
        cx, cy, cz = t * x, t * y, t * z
        r = teardrop_radius_modified(t)
        view.addSphere({
            'center': {'x': cx, 'y': cy, 'z': cz},
            'radius': r,
            'color': color,
            'opacity': 0.6
        })
    if include_ligand:
        view.addSphere({
            'center': {'x': x, 'y': y, 'z': z},
            'radius': 0.5,
            'color': color,
            'opacity': 0.9
        })
    else:
        t_electron = 0.5
        ex, ey, ez = t_electron * x, t_electron * y, t_electron * z
        p = perpendicular_vector((x, y, z))
        offset = 0.1
        for center in [(ex + offset * p[0], ey + offset * p[1], ez + offset * p[2]),
                       (ex - offset * p[0], ey - offset * p[1], ez - offset * p[2])]:
            view.addSphere({
                'center': {'x': center[0], 'y': center[1], 'z': center[2]},
                'radius': 0.1,
                'color': 'black',
                'opacity': 1.0
            })

def add_arc_between(view, v1, v2, segments=20, allow_180_label=False):
    u1, u2 = normalize(v1), normalize(v2)
    r = (((norm(v1) + norm(v2)) / 2.0) * 1.1)
    dp = dot_product(u1, u2)
    if abs(dp + 1.0) < 1e-6:
        angle, n_vec = math.pi, perpendicular_vector(u1)
    else:
        angle = math.acos(max(-1.0, min(1.0, dp)))
        n_vec = normalize((u2[0] - dp * u1[0], u2[1] - dp * u1[1], u2[2] - dp * u1[2]))
    arc_points = [(
        r * (u1[0] * math.cos(i / segments * angle) + n_vec[0] * math.sin(i / segments * angle)),
        r * (u1[1] * math.cos(i / segments * angle) + n_vec[1] * math.sin(i / segments * angle)),
        r * (u1[2] * math.cos(i / segments * angle) + n_vec[2] * math.sin(i / segments * angle))
    ) for i in range(segments + 1)]
    for i in range(len(arc_points) - 1):
        view.addCylinder({
            'start': {'x': arc_points[i][0], 'y': arc_points[i][1], 'z': arc_points[i][2]},
            'end': {'x': arc_points[i+1][0], 'y': arc_points[i+1][1], 'z': arc_points[i+1][2]},
            'radius': 0.02,
            'color': 'lightgray',
            'opacity': 0.5
        })
    mid_point = (
        r * (u1[0] * math.cos(angle / 2) + n_vec[0] * math.sin(angle / 2)),
        r * (u1[1] * math.cos(angle / 2) + n_vec[1] * math.sin(angle / 2)),
        r * (u1[2] * math.cos(angle / 2) + n_vec[2] * math.sin(angle / 2))
    )
    if not (abs(angle - math.pi) < 1e-6 and not allow_180_label):
        offset_vec = perpendicular_vector(mid_point)
        label_pos = (mid_point[0] + 0.15 * offset_vec[0],
                     mid_point[1] + 0.15 * offset_vec[1],
                     mid_point[2] + 0.15 * offset_vec[2])
        view.addLabel(f"{math.degrees(angle):.1f}°", {
            'position': {'x': label_pos[0], 'y': label_pos[1], 'z': label_pos[2]},
            'fontColor': 'black',
            'backgroundColor': 'transparent',
            'fontSize': 14,
            'showBackground': False
        })

def add_angle_labels(view, domains):
    for i in range(len(domains)):
        for j in range(i + 1, len(domains)):
            if domains[i]['type'] == 'bond' and domains[j]['type'] == 'bond':
                add_arc_between(view, domains[i]['pos'], domains[j]['pos'], segments=30,
                                allow_180_label=(len(domains) == 2))

def show_vsepr_teardrop(domains, shape_name, show_angle_labels=True):
    if len(domains) == 4:
        R = 2.5; s = R / math.sqrt(3)
        domains = [
            {"pos": (s, s, s), "type": domains[0]["type"]},
            {"pos": (s, -s, -s), "type": domains[1]["type"]},
            {"pos": (-s, s, -s), "type": domains[2]["type"]},
            {"pos": (-s, -s, s), "type": domains[3]["type"]}
        ]
    view = py3Dmol.view(width=360, height=360)
    add_axes(view, axis_length=3.0)
    view.addSphere({'center': {'x': 0, 'y': 0, 'z': 0},
                    'radius': 0.5,
                    'color': 'black',
                    'opacity': 1.0})
    for d in domains:
        x, y, z = d['pos']
        col = 'lightblue' if d['type'] == 'bond' else 'pink'
        inc = True if d['type'] == 'bond' else False
        add_teardrop_lobe(view, x, y, z, color=col, steps=20, include_ligand=inc)
    if show_angle_labels and all(d['type'] == 'bond' for d in domains):
        add_angle_labels(view, domains)
    
    if len(domains) == 2:
        view.rotate(90, 'y')
    elif len(domains) == 3:
        view.rotate(90, 'z')
    elif len(domains) == 6:
        if any(keyword in shape_name for keyword in ["平面四方", "T-shaped", "T形"]):
            pass
        elif any(keyword in shape_name for keyword in ["直線"]):
            view.rotate(90, 'z')
        else:
            view.rotate(90, 'x')
    else:
        view.rotate(-90, 'x')
    
    view.zoomTo()
    html_str = view._make_html().replace("background-color: white;", "background-color: transparent;")
    return html_str

# -------------------------------
# VSEPR 模型定義（2～6 電子域）
# -------------------------------
vsepr_geometries = {
    "2_0": {"shape_name": "2 電子域, 0 LP: Linear (直線)",
             "domains": [{"pos": (0, 0, 2.5), "type": "bond"},
                         {"pos": (0, 0, -2.5), "type": "bond"}]},
    "3_0": {"shape_name": "3 電子域, 0 LP: Trigonal Planar (平面三角)",
             "domains": [{"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-1.25, 2.165, 0), "type": "bond"},
                         {"pos": (-1.25, -2.165, 0), "type": "bond"}]},
    "3_1": {"shape_name": "3 電子域, 1 LP: Bent (角形)",
             "domains": [{"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-1.25, 2.165, 0), "type": "bond"},
                         {"pos": (-1.25, -2.165, 0), "type": "lp"}]},
    "4_0": {"shape_name": "4 電子域, 0 LP: 正四面體",
             "domains": [{"pos": (2.357, 0, -0.8333), "type": "bond"},
                         {"pos": (-1.1785, 2.0413, -0.8333), "type": "bond"},
                         {"pos": (-1.1785, -2.0413, -0.8333), "type": "bond"},
                         {"pos": (0, 0, 2.5), "type": "bond"}]},
    "4_1": {"shape_name": "4 電子域, 1 LP: Trigonal Pyramidal (三角錐)",
             "domains": [{"pos": (2.357, 0, -0.8333), "type": "lp"},
                         {"pos": (-1.1785, 2.0413, -0.8333), "type": "bond"},
                         {"pos": (-1.1785, -2.0413, -0.8333), "type": "bond"},
                         {"pos": (0, 0, 2.5), "type": "bond"}]},
    "4_2": {"shape_name": "4 電子域, 2 LP: Bent (角形)",
             "domains": [{"pos": (2.357, 0, -0.8333), "type": "lp"},
                         {"pos": (-1.1785, 2.0413, -0.8333), "type": "lp"},
                         {"pos": (-1.1785, -2.0413, -0.8333), "type": "bond"},
                         {"pos": (0, 0, 2.5), "type": "bond"}]},
    "5_0": {"shape_name": "5 電子域, 0 LP: Trigonal Bipyramidal (雙三角錐)",
             "domains": [{"pos": (0, 0, 2.5), "type": "bond"},
                         {"pos": (0, 0, -2.5), "type": "bond"},
                         {"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-1.25, 2.165, 0), "type": "bond"},
                         {"pos": (-1.25, -2.165, 0), "type": "bond"}]},
    "5_1": {"shape_name": "5 電子域, 1 LP: 蹺蹺板形",
             "domains": [{"pos": (0, 0, 2.5), "type": "bond"},
                         {"pos": (0, 0, -2.5), "type": "bond"},
                         {"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-1.25, 2.165, 0), "type": "bond"},
                         {"pos": (-1.25, -2.165, 0), "type": "lp"}]},
    "5_2": {"shape_name": "5 電子域, 2 LP: T-shaped (T形)",
             "domains": [{"pos": (0, 0, 2.5), "type": "bond"},
                         {"pos": (0, 0, -2.5), "type": "bond"},
                         {"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-1.25, 2.165, 0), "type": "lp"},
                         {"pos": (-1.25, -2.165, 0), "type": "lp"}]},
    "5_3": {"shape_name": "5 電子域, 3 LP: Linear (直線)",
             "domains": [{"pos": (0, 0, 2.5), "type": "bond"},
                         {"pos": (0, 0, -2.5), "type": "bond"},
                         {"pos": (2.5, 0, 0), "type": "lp"},
                         {"pos": (-1.25, 2.165, 0), "type": "lp"},
                         {"pos": (-1.25, -2.165, 0), "type": "lp"}]},
    "6_0": {"shape_name": "6 電子域, 0 LP: Octahedral (正八面體)",
             "domains": [{"pos": (0, 0, 2.5), "type": "bond"},
                         {"pos": (0, 0, -2.5), "type": "bond"},
                         {"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-2.5, 0, 0), "type": "bond"},
                         {"pos": (0, 2.5, 0), "type": "bond"},
                         {"pos": (0, -2.5, 0), "type": "bond"}]},
    "6_1": {"shape_name": "6 電子域, 1 LP: Square Pyramidal (金字塔型)",
             "domains": [{"pos": (0, 0, 2.5), "type": "lp"},
                         {"pos": (0, 0, -2.5), "type": "bond"},
                         {"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-2.5, 0, 0), "type": "bond"},
                         {"pos": (0, 2.5, 0), "type": "bond"},
                         {"pos": (0, -2.5, 0), "type": "bond"}]},
    "6_2": {"shape_name": "6 電子域, 2 LP: Square Planar (平面四邊)",
             "domains": [{"pos": (0, 0, 2.5), "type": "lp"},
                         {"pos": (0, 0, -2.5), "type": "lp"},
                         {"pos": (2.5, 0, 0), "type": "bond"},
                         {"pos": (-2.5, 0, 0), "type": "bond"},
                         {"pos": (0, 2.5, 0), "type": "bond"},
                         {"pos": (0, -2.5, 0), "type": "bond"}]},
    "6_3": {"shape_name": "6 電子域, 3 LP: T-shaped (T形)",
             "domains": [{"pos": (0, 0, 2.5), "type": "lp"},
                         {"pos": (0, 0, -2.5), "type": "lp"},
                         {"pos": (2.5, 0, 0), "type": "lp"},
                         {"pos": (-2.5, 0, 0), "type": "bond"},
                         {"pos": (0, 2.5, 0), "type": "bond"},
                         {"pos": (0, -2.5, 0), "type": "bond"}]},
    "6_4": {"shape_name": "6 電子域, 4 LP: Linear (直線)",
             "domains": [{"pos": (0, 0, 2.5), "type": "lp"},
                         {"pos": (0, 0, -2.5), "type": "lp"},
                         {"pos": (2.5, 0, 0), "type": "lp"},
                         {"pos": (-2.5, 0, 0), "type": "lp"},
                         {"pos": (0, 2.5, 0), "type": "bond"},
                         {"pos": (0, -2.5, 0), "type": "bond"}]}
}

# -------------------------------
# Streamlit 主程式
# -------------------------------
st.markdown("<h1 style='text-align: center;'>VSEPR 模型</h1>", unsafe_allow_html=True)

# 選擇電子域數（radio 水平排列）
domain_counts = sorted({key.split('_')[0] for key in vsepr_geometries.keys()}, key=int)
selected_count = st.radio("選擇電子域數", domain_counts, horizontal=True)

# 從該電子域數下依 LP 數排序的模型選項（radio 水平排列）
group_options = sorted([key for key in vsepr_geometries if key.startswith(selected_count)],
                       key=lambda x: int(x.split('_')[1]))
if not group_options:
    st.error("該電子域數下無模型！")
else:
    selected_key = st.radio("選擇模型", group_options, horizontal=True)

data = vsepr_geometries[selected_key]
show_angles = st.checkbox("顯示夾角標示", value=True) if all(d['type']=='bond' for d in data["domains"]) else False

html_str = show_vsepr_teardrop(data["domains"], data["shape_name"], show_angle_labels=show_angles)

# 模型名稱置中，字體 16px
st.markdown(f"<p style='font-size:16px; text-align:center;'>{data['shape_name']}</p>", unsafe_allow_html=True)

# 將 3D 模型 HTML 轉成 base64，再嵌入 iframe（外層尺寸 380×380，置中）
html_base64 = base64.b64encode(html_str.encode('utf-8')).decode('utf-8')
iframe_html = f"""
<iframe src="data:text/html;base64,{html_base64}" style="border:2px solid #000; width:380px; height:380px; box-sizing:border-box; display:block; margin:auto;" frameborder="0"></iframe>
"""
st.markdown(iframe_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------
# 加入像素風小貓（像素風、可移動）
# -------------------------------
st.markdown(
    """
    <style>
    #cat {
      position: fixed;
      bottom: 10px;
      right: 10px;
      width: 64px;
      height: 64px;
      cursor: pointer;
      z-index: 9999;
      image-rendering: pixelated;
      animation: moveCat 8s linear infinite;
    }
    @keyframes moveCat {
      0% { transform: translate(0, 0); }
      25% { transform: translate(-20px, -20px); }
      50% { transform: translate(-40px, 0); }
      75% { transform: translate(-20px, 20px); }
      100% { transform: translate(0, 0); }
    }
    </style>
    <img id="cat" src="https://i.imgur.com/JXK3Fif.png" alt="Pixel Cat">
    <script>
    const cat = document.getElementById('cat');
    cat.addEventListener('click', function() {
      // 當點擊小貓時，隨機移動位置（閃開效果）
      const randomX = Math.floor(Math.random() * 200) - 100;
      const randomY = Math.floor(Math.random() * 200) - 100;
      cat.style.transform = `translate(${randomX}px, ${randomY}px)`;
    });
    </script>
    """,
    unsafe_allow_html=True
)
