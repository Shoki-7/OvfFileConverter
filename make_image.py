from PyQt5.QtGui import QImage, QPixmap
import matplotlib.pyplot as plt
from io import BytesIO
from PyQt5.QtCore import Qt
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1 import Divider, Size
import numpy as np
import os

from PIL import Image

import matplotlib
matplotlib.use('Agg')

def gen_cmap_rgb(cols):
    nmax = float(len(cols)-1)
    cdict = {'red':[], 'green':[], 'blue':[]}
    for n, c in enumerate(cols):
        loc = n/nmax
        cdict['red'  ].append((loc, c[0], c[0]))
        cdict['green'].append((loc, c[1], c[1]))
        cdict['blue' ].append((loc, c[2], c[2]))
    return LinearSegmentedColormap('cmap', cdict)

def get_colormap(variables):
    cmap = variables["Colormap"]
    is_Reverse = variables["is_Reverse"]
    if "special" in cmap and not is_Reverse:
        cmap = gen_cmap_rgb([(0,0,0.5),(0,0,1),(0,1,1),(0,1,0),(1,1,0),(1,0.5,0),(1,0,0)])
    elif "special" in cmap and is_Reverse:
        cmap = gen_cmap_rgb([(1,0,0),(1,0.5,0),(1,1,0),(0,1,0),(0,1,1),(0,0,1),(0,0,0.5)])
    elif is_Reverse:
        cmap = cmap + "_r"

    return cmap

def get_multiplier(prefix):
    si_prefixes = {
        "Y": 10**24,  # ヨタ
        "Z": 10**21,  # ゼタ
        "E": 10**18,  # エクサ
        "P": 10**15,  # ペタ
        "T": 10**12,  # テラ
        "G": 10**9,   # ギガ
        "M": 10**6,   # メガ
        "k": 10**3,   # キロ
        "h": 10**2,   # ヘクト
        "da": 10**1,  # デカ
        "": 1,        # 基本単位
        "d": 10**-1,  # デシ
        "c": 10**-2,  # センチ
        "m": 10**-3,  # ミリ
        "μ": 10**-6,  # マイクロ
        "n": 10**-9,  # ナノ
        "p": 10**-12, # ピコ
        "f": 10**-15, # フェムト
        "a": 10**-18, # アト
        "z": 10**-21, # ゼプト
        "y": 10**-24  # ヨクト
    }

    return si_prefixes[prefix]

def figure_setting(graph_font_size):
    label_font_size = graph_font_size[0]
    label_padding = graph_font_size[1]
    tick_label_font_size = graph_font_size[2]
    tick_padding = graph_font_size[3]

    plt.rcParams['pdf.fonttype'] = 42           #true type font
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['font.family'] = 'Arial'       #text font
    plt.rcParams["mathtext.fontset"] = "dejavusans"
    plt.rcParams['font.size'] = 8              #size of font
    plt.rcParams['xtick.labelsize'] = tick_label_font_size        #font size of x-axis scale label
    plt.rcParams['ytick.labelsize'] = tick_label_font_size        #font size of y-axis scale label
    plt.rcParams['xtick.direction'] = 'in'      #Whether the x-axis scale line is inward ('in'), outward ('out') or bi-directional ('inout').
    plt.rcParams['ytick.direction'] = 'in'      #Whether the y-axis scale line is inward ('in'), outward ('out') or bi-directional ('inout').
    plt.rcParams['xtick.major.width'] = 0.5     #Line width of x-axis main scale line
    plt.rcParams['ytick.major.width'] = 0.5     #Line width of y-axis main scale line
    plt.rcParams['axes.linewidth'] = 0.5        #Line width of axis
    plt.rcParams['xtick.major.pad'] = tick_padding         #Distance between scale and scale label of x-axis
    plt.rcParams['ytick.major.pad'] = tick_padding - 1         #Distance between scale and scale label of y-axis
    plt.rcParams['xtick.top'] = True            #Upper scale of x-axis
    plt.rcParams['ytick.right'] = True          #Upper scale of y-axis
    plt.rcParams['text.usetex'] = False
    plt.rcParams['axes.labelsize'] = label_font_size
    plt.rcParams['axes.labelpad'] = label_padding
    return plt

def figure_size_setting(aspect, ax_margin_inch, cbar_width_inch, graph_cbar_distance_inch, is_show_cbar, is_show_axis, graph_font_size, is_colorbar_bottom=False):
    plt = figure_setting(graph_font_size)

    if aspect > 1:
        ax_w_px = 1000
        ax_h_px = max(1, int(ax_w_px / aspect))
    else:
        ax_h_px = 1000
        ax_w_px = max(1, int(ax_h_px * aspect))

    fig_dpi = 300
    ax_w_inch = ax_w_px / fig_dpi
    ax_h_inch = ax_h_px / fig_dpi

    if is_colorbar_bottom:
        fig_w_inch = ax_w_inch + ax_margin_inch[0] + ax_margin_inch[2]
        fig_h_inch = ax_h_inch + ax_margin_inch[1] + ax_margin_inch[3] + cbar_width_inch + graph_cbar_distance_inch
    else:
        fig_w_inch = ax_w_inch + ax_margin_inch[0] + ax_margin_inch[2] + cbar_width_inch + graph_cbar_distance_inch
        fig_h_inch = ax_h_inch + ax_margin_inch[1] + ax_margin_inch[3]

    fig = plt.figure(dpi=fig_dpi, figsize=(fig_w_inch, fig_h_inch))

    # Dividerの設定
    if is_show_cbar:
        if is_colorbar_bottom:
            h = [Size.Fixed(ax_margin_inch[0]), 
                Size.Fixed(ax_w_inch)]
            v = [Size.Fixed(ax_margin_inch[1]),    # 下余白
                Size.Fixed(cbar_width_inch),    # カラーバーの高さ
                Size.Fixed(graph_cbar_distance_inch),   # プロットとカラーバーの間のマージン
                Size.Fixed(ax_h_inch)]  # プロット領域の高さ
        else:
            h = [Size.Fixed(ax_margin_inch[0]),  # 左余白
                Size.Fixed(ax_w_inch),          # プロット領域の幅
                Size.Fixed(graph_cbar_distance_inch),  # プロットとカラーバーの間のマージン
                Size.Fixed(cbar_width_inch)]    # カラーバーの幅
            v = [Size.Fixed(ax_margin_inch[1]),  # 下余白
                Size.Fixed(ax_h_inch)]          # プロット領域の高さ
    else:
        h = [Size.Fixed(ax_margin_inch[0]),  # 左余白
            Size.Fixed(ax_w_inch)]         # プロット領域の幅
        v = [Size.Fixed(ax_margin_inch[1]),  # 下余白
            Size.Fixed(ax_h_inch)]         # プロット領域の高さ
    
    divider = Divider(fig, (0, 0, 1, 1), h, v, aspect=False)

    # プロット領域
    if is_colorbar_bottom and is_show_cbar:
        ax = fig.add_axes(divider.get_position(), axes_locator=divider.new_locator(nx=1, ny=3))
    else:
        ax = fig.add_axes(divider.get_position(), axes_locator=divider.new_locator(nx=1, ny=1))

    if not is_show_axis:
        ax.axis("off")

    # カラーバー領域
    if is_show_cbar:
        if is_colorbar_bottom:
            cax = fig.add_axes(divider.get_position(), axes_locator=divider.new_locator(nx=1, ny=1))
        else:
            cax = fig.add_axes(divider.get_position(), axes_locator=divider.new_locator(nx=3, ny=1))
    else:
        cax = None

    return plt, fig, ax, cax

def get_tick_label(tick_label):
    try:
        # Check if the input is an empty string
        if tick_label.strip() == "":
            return None
        
        # Split the string by commas and convert to a list of strings
        tick_array = [float(x.strip()) for x in tick_label.split(",")]
        return tick_array
    except Exception:
        return None

def make_image(self, array, variables, mode="check", saved_name="", arrow_azimuthal_angle_array=None, arrow_magnitude_xy_array=None):
    is_show_axis = variables["Show Axis"]
    is_show_cbar = variables["Show Colorbar"]
    is_colorbar_bottom = variables["Colorbar Bottom"]

    is_x_axis_reverse = variables["X-Axis Reverse"]
    is_y_axis_reverse = variables["Y-Axis Reverse"]

    if is_x_axis_reverse:
        array = np.flip(array, axis=1)
    if is_y_axis_reverse:
        array = np.flip(array, axis=0)

    x_multiplier = get_multiplier(variables["X-Axis SI prefix"])
    y_multiplier = get_multiplier(variables["Y-Axis SI prefix"])
    
    Sizex = variables["Size" + variables["Graph X-Axis"]] if variables["Size" + variables["Graph X-Axis"]] is None else variables["Size" + variables["Graph X-Axis"]] / x_multiplier
    Sizey = variables["Size" + variables["Graph Y-Axis"]] if variables["Size" + variables["Graph Y-Axis"]] is None else variables["Size" + variables["Graph Y-Axis"]] / y_multiplier

    aspect_ratio_width = variables["Aspect ratio width"]
    aspect_ratio_height = variables["Aspect ratio height"]
    if None in (aspect_ratio_width, aspect_ratio_height):
        if None in (Sizex, Sizey):
            aspect = array.shape[1] / array.shape[0] # yoko/tate
        else:
            aspect = Sizex / Sizey if is_show_axis else array.shape[1] / array.shape[0]
    else:
        aspect = aspect_ratio_width / aspect_ratio_height # yoko/tate

    vmin = variables["Z-Axis Displayed range min"]
    vmax = variables["Z-Axis Displayed range max"]

    extent = (0, array.shape[1]-1) + (0, array.shape[0]-1)
    is_xaxis_range = False
    is_yaxis_range = False

    x_overall_range = (variables["X-Axis Overall range min"] if variables["X-Axis Overall range min"] is None else variables["X-Axis Overall range min"] / x_multiplier, variables["X-Axis Overall range max"] if variables["X-Axis Overall range max"] is None else variables["X-Axis Overall range max"] / x_multiplier)
    x_displayed_range = (variables["X-Axis Displayed range min"] if variables["X-Axis Displayed range min"] is None else variables["X-Axis Displayed range min"] / x_multiplier, variables["X-Axis Displayed range max"] if variables["X-Axis Displayed range max"] is None else variables["X-Axis Displayed range max"] / x_multiplier)

    y_overall_range = (variables["Y-Axis Overall range min"] if variables["Y-Axis Overall range min"] is None else variables["Y-Axis Overall range min"] / y_multiplier, variables["Y-Axis Overall range max"] if variables["Y-Axis Overall range max"] is None else variables["Y-Axis Overall range max"] / y_multiplier)
    y_displayed_range = (variables["Y-Axis Displayed range min"] if variables["Y-Axis Displayed range min"] is None else variables["Y-Axis Displayed range min"] / y_multiplier, variables["Y-Axis Displayed range max"] if variables["Y-Axis Displayed range max"] is None else variables["Y-Axis Displayed range max"] / y_multiplier)

    if is_show_axis:
        if None in x_overall_range:
            x_range = (0, array.shape[1]-1)
        else:
            x_range = x_overall_range
            is_xaxis_range = True
        
        if None in y_overall_range:
            y_range = (0, array.shape[0]-1)
        else:
            y_range = y_overall_range
            is_yaxis_range = True

        extent = x_range + y_range

    left_margin_inch = variables["Left"]
    top_margin_inch = variables["Top"]
    right_margin_inch = variables["Right"]
    bottom_margin_inch = variables["Bottom"]

    if is_show_axis:
        ax_margin_inch = (left_margin_inch, bottom_margin_inch, right_margin_inch, top_margin_inch)    # Left,Top,Right,Bottom [inch]       
    elif is_show_cbar:
        ax_margin_inch = (0, bottom_margin_inch, right_margin_inch, top_margin_inch)    # Left,Top,Right,Bottom [inch]
    else:
        ax_margin_inch = (0, 0, 0, 0)    # Left,Top,Right,Bottom [inch]
    
    if is_show_cbar:
        array /= get_multiplier(variables["Z-Axis SI prefix"])
    
    cbar_width_inch = variables["Colorbar Width"] if is_show_cbar else 0
    graph_cbar_distance_inch = variables["Between Graph and Colorbar"]  if is_show_cbar else 0

    graph_font_size = (variables["Label font size"], variables["Label padding"], variables["Tick label font size"], variables["Tick label padding"])
    
    plt, fig, ax, cax = figure_size_setting(aspect, ax_margin_inch, cbar_width_inch, graph_cbar_distance_inch, is_show_cbar, is_show_axis, graph_font_size, is_colorbar_bottom)

    cmap = get_colormap(variables)
    if array.ndim == 2:
        im = ax.imshow(array, origin='lower', extent=extent, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    elif array.ndim == 3:
        im = ax.imshow(array, origin='lower', extent=extent, aspect="auto")
    
    if is_show_axis:
        x_label = variables["X-Axis Label"] + " (" + variables["X-Axis SI prefix"] + variables["X-Axis Unit"] + ")"
        y_label = variables["Y-Axis Label"] + " (" + variables["Y-Axis SI prefix"] + variables["Y-Axis Unit"] + ")"
        ax.set_xlabel(x_label, labelpad=graph_font_size[1]-1)
        ax.set_ylabel(y_label)
        ax.set_xlim(x_displayed_range)
        ax.set_ylim(y_displayed_range)
        x_tick_label = get_tick_label(variables["X-Axis Tick Label"])
        y_tick_label = get_tick_label(variables["Y-Axis Tick Label"])
        if x_tick_label:
            ax.set_xticks(x_tick_label)
        if y_tick_label:
            ax.set_yticks(y_tick_label)
    
    arrow_flag = variables["Show Arrows"]
    if arrow_flag and arrow_magnitude_xy_array is not None and arrow_azimuthal_angle_array is not None:
        print("make_image -  extent:", extent)
        nx, ny = array.shape[0], array.shape[1]
        block_size = variables["Block Size"]
        start_x = (nx % block_size) // 2 if nx > block_size else 0
        stop_x = nx + start_x - (nx % block_size) if nx > block_size else nx
        start_y = (ny % block_size) // 2 if ny > block_size else 0
        stop_y = ny + start_y - (ny % block_size) if ny > block_size else ny
        averaged_array_x_len = block_size if nx > block_size else nx
        averaged_array_y_len = block_size if ny > block_size else ny

        x0 = extent[0]
        dx = (extent[1] - extent[0])/(array.shape[1]) if is_xaxis_range else (extent[1] - extent[0])/(array.shape[1] - 1)
        y0 = extent[2]
        dy = (extent[3] - extent[2])/(array.shape[0]) if is_yaxis_range else (extent[3] - extent[2])/(array.shape[0] - 1)

        print("make_image -  x0, dx:", x0, dx)
        print("make_image -  y0, dy:", y0, dy)
        
        x, y = np.meshgrid(np.arange(start_y + (averaged_array_y_len - 1)/2, stop_y, block_size) * dx + x0, np.arange(start_x + (averaged_array_x_len - 1)/2, stop_x, block_size) * dy + y0)

        print("make_image -  x.shape:", x.shape)
        # print("make_image -  x:", x)
        # print("make_image -  y:", y)

        arrow_size_factor = variables["Arrow Lnegth"]   # length
        arrow_width = variables["Arrow Width"]     # size
        arrow_color = variables["Arrow Color"] or "white"

        standard_arrow_size = np.min([block_size * dx, block_size * dy]) * 0.9

        # nx, ny = arrow_azimuthal_angle_array.shape
        # x, y = np.meshgrid(np.arange(ny), np.arange(nx))

        # Compute vector components from azimuthal angle and magnitude
        u = arrow_magnitude_xy_array * np.cos(arrow_azimuthal_angle_array)  # x-component
        v = arrow_magnitude_xy_array * np.sin(arrow_azimuthal_angle_array)  # y-component

        # Scale arrow sizes so that the largest arrow fits within the standard_arrow_size
        magnitude = np.sqrt(u**2 + v**2)
        max_magnitude = np.max(magnitude)

        if max_magnitude > 0:  # Avoid division by zero
            scale_factor = standard_arrow_size / max_magnitude
        else:
            scale_factor = 1  # Default scale factor when all magnitudes are zero

        u *= scale_factor * arrow_size_factor
        v *= scale_factor * arrow_size_factor

        # print("make_image -  u:", u)
        # print("make_image -  v:", v)

        plt.quiver(
            x, y, u, v,
            angles='xy', scale_units='xy', scale=1, alpha=1,
            pivot='mid', units='inches',
            color=arrow_color,
            width=arrow_width,  # 矢印の線の幅
            headwidth=4,  # 矢じりの幅 (単位: 矢印全体の幅との比率)
            headlength=5,  # 矢じりの長さ (単位: 矢印全体の長さとの比率)
            headaxislength=4,  # 矢じりの基部から先端までの長さ (単位: 矢印全体の長さとの比率)
            minlength=0.1,  # 矢印の最小長 (短すぎる矢印を描画しない)
            minshaft=1  # 矢印のシャフト部分の最小長さ (単位: 幅との比率)
        )

        # ax.quiver(
        #     x, y, u, v, arrow_azimuthal_angle_array, cmap=cmap,
        #     angles='xy', scale_units='xy', scale=1, alpha=1,
        #     pivot='mid', units='inches',
        #     width=arrow_width,  # 矢印の線の幅
        #     headwidth=4,  # 矢じりの幅 (単位: 矢印全体の幅との比率)
        #     headlength=5,  # 矢じりの長さ (単位: 矢印全体の長さとの比率)
        #     headaxislength=4,  # 矢じりの基部から先端までの長さ (単位: 矢印全体の長さとの比率)
        #     minlength=0.1,  # 矢印の最小長 (短すぎる矢印を描画しない)
        #     minshaft=1  # 矢印のシャフト部分の最小長さ (単位: 幅との比率)
        # )

    if is_show_cbar:
        # cb = fig.colorbar(im, cax=cax)
        cb = fig.colorbar(im, cax=cax, orientation="horizontal" if is_colorbar_bottom else "vertical")
        z_label = variables["Z-Axis Label"] + " (" + variables["Z-Axis SI prefix"] + variables["Z-Axis Unit"] + ")" if not variables["Z-Axis Unit"] in ["a.u.", "arb.units", "arb.unit"] else  variables["Z-Axis Label"] + " (" + variables["Z-Axis Unit"] + ")"
        if is_colorbar_bottom:
            cb.set_label(z_label, labelpad=graph_font_size[1] - 1)
        else:
            cb.set_label(z_label, labelpad=graph_font_size[1])
        z_tick_label = get_tick_label(variables["Z-Axis Tick Label"])
        if z_tick_label:
            cb.set_ticks(z_tick_label)

    saved_dpi = variables["dpi"]

    if mode == "save":
        output_file_name = saved_name + '.' + variables["Extension"]
        output_file_path = os.path.join(variables["Input Directory"], output_file_name)
        
        # plt.tight_layout()
        plt.savefig(output_file_path, transparent=True, dpi=saved_dpi, bbox_inches='tight')

    if mode == "animation":
        # MatplotlibのプロットをQPixmapに変換
        buf = BytesIO()
        plt.savefig(buf, format="png", transparent=False, dpi=saved_dpi)
        buf.seek(0)
        plt.clf()
        plt.close()

        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue(), "PNG")
        
        # QLabel (graph_display) のサイズに合わせてリサイズ
        label_width = self.graph_display.width()
        label_height = self.graph_display.height()
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return pixmap, scaled_pixmap
    
    else:
        # MatplotlibのプロットをQPixmapに変換
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.clf()
        plt.close()

        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue(), "PNG")

        # QLabel (graph_display) のサイズに合わせてリサイズ
        label_width = self.graph_display.width()
        label_height = self.graph_display.height()
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return scaled_pixmap


def create_gif(self, frames, variables):
    output_file_name = os.path.basename(variables["Input Directory"]) + ".gif"
    output_file_path = os.path.join(variables["Input Directory"], output_file_name)
    speed = variables["GIF animation speed"]  # デフォルト速度: 100ms

    pil_images = []

    for pixmap in frames:
        if pixmap:
            # QPixmap を QImage に変換 (ARGB32)
            qt_image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
            width, height = qt_image.width(), qt_image.height()

            # QImage から RGBA データを取得して PIL Image に変換
            buffer = qt_image.bits().asstring(width * height * 4)  # 4バイト (RGBA)
            pil_image = Image.frombytes("RGBA", (width, height), buffer)

            # RGB に変換して透明度を削除 (GIFは透明度に対応しない場合あり)
            pil_image = pil_image.convert("RGB")

            pil_images.append(pil_image)

    if pil_images:
        # GIF アニメーションを保存
        pil_images[0].save(
            output_file_path,
            save_all=True,
            append_images=pil_images[1:],
            duration=speed,
            loop=0
        )