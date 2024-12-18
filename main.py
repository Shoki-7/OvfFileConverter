import sys
import ctypes
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QGridLayout, QFileDialog, QGroupBox, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot
from PyQt5.QtGui import QIcon

from concurrent.futures import ThreadPoolExecutor
import threading

import read_ovf_files as rof
import os
import glob
import numpy as np
import json

import make_image as mi
import colormap_stocks as cs
import get_array as ga
import get_icon as gi

try:
    import footer_widget as fw
    footer_available = True
except ImportError:
    footer_available = False

# footer_available = False

def get_windows_display_scale():
    hdc = ctypes.windll.user32.GetDC(0)
    dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    return dpi / 96.0


scale_factor = get_windows_display_scale()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Adjust dimensions by scale_factor
        window_width = int(1700 * scale_factor)
        window_height = int(750 * scale_factor)

        self.setWindowTitle("OVF Files Visualization Tool")
        self.setGeometry(100, 100, window_width, window_height)
        self.setFixedSize(window_width, window_height)

        is_debug = False

        # Set the style sheet for the main window
        font_size = f"{int(14 * scale_factor)}px"
        label_color = "#333333"
        background_color = "#ffffff"
        self.checked_border_color = "#808080"
        self.unchecked_border_color = "#cccccc"
        self.conflict_border_color = "red"
        button_background_color = "#0078d7"
        button_hover_color = "#005a9e"
        graph_background_color = "#f5f5f5"
        border_radius = f"{int(5 * scale_factor)}px"
        self.border_width = f"{int(1 * scale_factor)}px"
        self.conflict_border_width = f"{int(1 * scale_factor)}px"
        padding_value = f"{int(5 * scale_factor)}px"
        button_padding = f"{int(5 * scale_factor)}px {int(10 * scale_factor)}px"
        font_family = "Arial"
        footer_font_size = f"{int(12 * scale_factor)}px"
        footer_background_color = "#f5f5f5"
        footer_font_color = "black"

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {background_color};
            }}
            QLabel {{
                font-size: {font_size};
                font-family: {font_family};
                color: {label_color};
            }}
            QLabel[html=true] {{
                font-size: {font_size};
                font-family: {font_family};
                color: {label_color};
            }}
            QLineEdit {{
                border: {self.border_width} solid {self.checked_border_color};
                border-radius: {border_radius};
                padding: {padding_value};
                font-size: {font_size};
                font-family: {font_family};
            }}
            QPushButton {{
                background-color: {button_background_color};
                color: #ffffff;
                border: none;
                border-radius: {border_radius};
                padding: {button_padding};
            }}
            QPushButton:hover {{
                background-color: {button_hover_color};
            }}
            QComboBox {{
                border: {self.border_width} solid {self.checked_border_color};
                border-radius: {border_radius};
                padding: {padding_value};
                font-size: {font_size};
                font-family: {font_family};
            }}
            QCheckBox {{
                font-size: {font_size};
                font-family: {font_family};
                color: {label_color};
            }}
            QGroupBox {{
                font-size: {font_size};
                font-family: {font_family};
                color: {label_color};
            }}
            QLabel#graph_display {{
                background-color: {graph_background_color};
                border: {self.border_width} solid {self.checked_border_color};
            }}
        """)

        # QLineEdit width
        unit_width = int(42 * scale_factor)
        range_width = int(70 * scale_factor)
        graph_axis_width = int(40 * scale_factor)
        aspect_width = int(45 * scale_factor)
        colormap_width = int(145 * scale_factor)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        main_layout = QHBoxLayout()  # 左右を分けるレイアウト
        footer_layout = QVBoxLayout()
        left_layout = QVBoxLayout()  # 左側のレイアウト
        right_layout = QVBoxLayout()  # 右側のレイアウト

        # Input path (directory only)
        input_layout = QHBoxLayout()
        input_label = QLabel("Input Directory:")
        if is_debug:
            self.input_line = QLineEdit(os.path.join(os.getcwd(), "TestOvfFiles2"))
        else:
            self.input_line = QLineEdit()    
        input_browse = QPushButton("Browse")
        input_browse.setFixedSize(int(80 * scale_factor), int(30 * scale_factor))
        input_browse.clicked.connect(self.browse_input)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(input_browse)
        left_layout.addLayout(input_layout)

        # Grid size inputs with HTML-styled labels (3x6 layout)
        input_grid_layout = QGridLayout()

        # 入力用
        input_grid_data = [
            # Row 0
            ("<i>N<sub>x</sub></i> :", "Nx", "100"),
            (", <i>N<sub>y</sub></i> :", "Ny", "100"),
            (", <i>N<sub>z</sub></i> :", "Nz", "100"),

            # Row 1
            ("Size<i><sub>x</sub></i> (m) :", "Sizex", "200e-6"),
            (", Size<i><sub>y</sub></i> (m) :", "Sizey", "200e-6"),
            (", Size<i><sub>z</sub></i> (m) :", "Sizez", "40e-9"),
        ]

        self.grid_inputs = {}

        # 入力部分 (Row 0, Row 1)
        for index, (label, key, placeholder) in enumerate(input_grid_data):
            row = index // 3  # 行番号 (3列ごとに新しい行)
            col = (index % 3) * 2  # 列番号 (ラベルと入力を2つの列で占有)

            # ラベルの作成
            lbl = QLabel(label)
            lbl.setProperty("html", True)
            input_grid_layout.addWidget(lbl, row, col)  # ラベルを配置

            # テキスト入力フィールドを作成
            input_field = QLineEdit()
            if placeholder:
                input_field.setPlaceholderText(placeholder)
            if key[0] == "N":
                input_field.setReadOnly(True)
            self.grid_inputs[key] = input_field
            input_grid_layout.addWidget(input_field, row, col + 1)  # 入力フィールドを配置
        
        left_layout.addLayout(input_grid_layout)


        output_grid_layout = QGridLayout()

        # 出力用
        output_grid_data = [
            # Row 2
            ("Output Format :", "Output Format", None),
            (", Plane index :", "Plane index", None),
            (", Graph X-Axis :", "Graph X-Axis", None),
            (", Y-Axis :", "Graph Y-Axis", None),
            (", Aspect ratio :", "Aspect ratio width", "1"),
            (" : ", "Aspect ratio height", "1")
        ]

        self.format_combo = None
        self.axis_combos = []        
        self.index_combo = None

        # 出力部分 (Row 2)
        for index, (label, key, placeholder) in enumerate(output_grid_data):
            row = index // 6  # 行番号 (3列ごとに新しい行)
            col = (index % 6) * 2  # 列番号 (ラベルと入力を2つの列で占有)

            # ラベルの作成
            lbl = QLabel(label)
            lbl.setProperty("html", True)
            if " : " in label:
                output_grid_layout.addWidget(lbl, row, col, Qt.AlignCenter)
            else:
                output_grid_layout.addWidget(lbl, row, col)  # ラベルを配置
            
            if "Aspect" in key:
                input_field = QLineEdit()
                if "Aspect" in key:
                    input_field.setFixedWidth(aspect_width)
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                self.grid_inputs[key] = input_field
                output_grid_layout.addWidget(input_field, row, col + 1)
            else:
                combo = QComboBox()
                if key == "Output Format":
                    self.format_combo = combo
                    combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                elif key == "Graph X-Axis":
                    combo.addItems(["x", "y", "z"])
                    combo.setCurrentText("x")  # 初期値
                    combo.setFixedWidth(graph_axis_width)
                    self.axis_combos.append(combo)
                    # combo.currentIndexChanged.connect(lambda: self.update_axis_options("Graph X-Axis"))
                elif key == "Graph Y-Axis":
                    combo.addItems(["x", "y", "z"])
                    combo.setCurrentText("y")  # 初期値
                    combo.setFixedWidth(graph_axis_width)
                    self.axis_combos.append(combo)
                    # combo.currentIndexChanged.connect(lambda: self.update_axis_options("Graph Y-Axis"))
                elif key == "Plane index":
                    self.index_combo = combo
                    combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)             

                output_grid_layout.addWidget(combo, row, col + 1)  # コンボボックスを配置

        left_layout.addLayout(output_grid_layout)


        # Colormap options layout
        colormap_grid_layout = QGridLayout()

        # Colormap option data
        colormap_grid_data = [
            ("Colormap :", "Colormap", None),
            (", Reverse :", "is_Reverse", None),
            (", Colormap range :", "Z-Axis Displayed range min", "-0.5"),
            (" ≤ <i>z</i> ≤ ", "Z-Axis Displayed range max", "0.5")
        ]
        
        self.colormap_combo = None  # Initialize as None

        # Colormap options
        for index, (label, key, placeholder) in enumerate(colormap_grid_data):
            row = index // 4  # 行番号 (3列ごとに新しい行)
            col = (index % 4) * 2  # 列番号 (ラベルと入力を2つの列で占有)

            # Create label
            lbl = QLabel(label)
            lbl.setProperty("html", True)
            if "≤ <i>" in label:
                colormap_grid_layout.addWidget(lbl, row, col, Qt.AlignCenter)
            else:
                colormap_grid_layout.addWidget(lbl, row, col)

            if key in ["is_Reverse"]:
                # Create checkbox for Show Arrows and Show Axis
                checkbox = QCheckBox()
                self.grid_inputs[key] = checkbox
                colormap_grid_layout.addWidget(checkbox, row, col + 1)  # Add checkbox to the grid
            elif key == "Colormap":
                # Create combo box for Colormap
                combo = QComboBox()
                combo.setFixedWidth(colormap_width)
                self.colormap_combo = combo
                colormap_grid_layout.addWidget(combo, row, col + 1)  # Add combo box to the grid
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                self.grid_inputs[key] = input_field
                colormap_grid_layout.addWidget(input_field, row, col + 1)

        # Add the Colormap options layout to the main layout
        left_layout.addLayout(colormap_grid_layout)
        

        # Show Axis全体を囲うグループボックスを作成
        self.show_axis_group = QGroupBox("Show Axis")
        self.show_axis_group.setCheckable(True)
        self.show_axis_group.setChecked(False)
        self.show_axis_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        show_axis_layout = QVBoxLayout()  # 縦方向にレイアウト

        # group box の cheak box でテキストカラーを変更
        self.show_axis_group.toggled.connect(lambda: self.toggle_group_box_text_color(self.show_axis_group))

        # X-Axis Group
        x_axis_group = QGroupBox("X-Axis")
        x_axis_layout = QGridLayout()

        # Axsis Setting
        self.prefix_combos = []

        # X-Axisの設定データ
        x_axis_data = [
            ("Overall range (m) :", "X-Axis Overall range min", "-100e-6"),
            (" ≤ <i>x</i> ≤ ", "X-Axis Overall range max", "100e-6"),
            (", Label :", "X-Axis Label", "Position $x$"),
            (", Unit :", "X-Axis Unit", "m"),
            (", SI prefix :", "X-Axis SI prefix", None),
            ("Displayed range (m) :", "X-Axis Displayed range min", "-50e-6"),
            (" ≤ <i>x</i> ≤ ", "X-Axis Displayed range max", "50e-6"),
            (", Tick Label :", "X-Axis Tick Label", "-60, -45, -30, -15, 0, 15, 30, 45, 60"),
            (", Reverse :", "X-Axis Reverse", None)
        ]

        # X-Axisオプションを配置
        col_offset = 0
        for index, (label, key, placeholder) in enumerate(x_axis_data):
            row = index // 5
            col = (index % 5) * 2 + col_offset

            lbl = QLabel(label)
            lbl.setProperty("html", True)
            if "≤ <i>" in label:
                x_axis_layout.addWidget(lbl, row, col, Qt.AlignCenter)
            else:
                x_axis_layout.addWidget(lbl, row, col)

            if "prefix" in key:
                combo = QComboBox()
                combo.addItems(["Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da", "", "d", "c", "m", "μ", "n", "p", "f", "a", "z", "y"])
                combo.setCurrentText("")
                self.prefix_combos.append(combo)
                x_axis_layout.addWidget(combo, row, col + 1)
            elif "Reverse" in key:
                checkbox = QCheckBox()
                self.grid_inputs[key] = checkbox
                x_axis_layout.addWidget(checkbox, row, col + 1)
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                if "Unit" in key:
                    input_field.setFixedWidth(unit_width)
                if "range" in key:
                    input_field.setFixedWidth(range_width)
                self.grid_inputs[key] = input_field
                if "Tick Label" in key:
                    x_axis_layout.addWidget(input_field, row, col + 1, 1, 3)
                    col_offset = 2
                else:
                    x_axis_layout.addWidget(input_field, row, col + 1)

        x_axis_group.setLayout(x_axis_layout)

        # Y-Axis Group
        y_axis_group = QGroupBox("Y-Axis")
        y_axis_layout = QGridLayout()

        # Y-Axisの設定データ
        y_axis_data = [
            ("Overall range (m) :", "Y-Axis Overall range min", "-100e-6"),
            (" ≤ <i>y</i> ≤ ", "Y-Axis Overall range max", "100e-6"),
            (", Label :", "Y-Axis Label", "Position $y$"),
            (", Unit :", "Y-Axis Unit", "m"),
            (", SI prefix :", "Y-Axis SI prefix", None),
            ("Displayed range (m) :", "Y-Axis Displayed range min", "-50e-6"),
            (" ≤ <i>y</i> ≤ ", "Y-Axis Displayed range max", "50e-6"),
            (", Tick Label :", "Y-Axis Tick Label", "-60, -45, -30, -15, 0, 15, 30, 45, 60"),
            (", Reverse :", "Y-Axis Reverse", None)
        ]

        # Y-Axisオプションを配置
        col_offset = 0
        for index, (label, key, placeholder) in enumerate(y_axis_data):
            row = index // 5
            col = (index % 5) * 2 + col_offset

            lbl = QLabel(label)
            lbl.setProperty("html", True)
            if "≤ <i>" in label:
                y_axis_layout.addWidget(lbl, row, col, Qt.AlignCenter)
            else:
                y_axis_layout.addWidget(lbl, row, col)

            if "prefix" in key:
                combo = QComboBox()
                combo.addItems(["Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da", "", "d", "c", "m", "μ", "n", "p", "f", "a", "z", "y"])
                combo.setCurrentText("")
                self.prefix_combos.append(combo)
                y_axis_layout.addWidget(combo, row, col + 1)
            elif "Reverse" in key:
                checkbox = QCheckBox()
                self.grid_inputs[key] = checkbox
                y_axis_layout.addWidget(checkbox, row, col + 1)
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                if "Unit" in key:
                    input_field.setFixedWidth(unit_width)
                if "range" in key:
                    input_field.setFixedWidth(range_width)
                self.grid_inputs[key] = input_field
                if "Tick Label" in key:
                    y_axis_layout.addWidget(input_field, row, col + 1, 1, 3)
                    col_offset = 2
                else:
                    y_axis_layout.addWidget(input_field, row, col + 1)

        y_axis_group.setLayout(y_axis_layout)

        # Graph Settings Group
        graph_setting_group = QGroupBox("Graph settings")
        graph_setting_layout = QGridLayout()

        # Graph settingsの設定データ
        graph_setting_data = [
            ("Left (inch) :", "Left", "0.7"),
            (", Top (inch) :", "Top", "0.5"),
            (", Right (inch) :", "Right", "0.7"),
            (", Bottom (inch) :", "Bottom", "0.5"),
            ("Label font size :", "Label font size", "11"),
            (", Label padding :", "Label padding", "4"),
            (", Tick label font size :", "Tick label font size", "10"),
            (", Tick label padding :", "Tick label padding", "4")
        ]

        # Graph Settingsオプションを配置
        for index, (label, key, placeholder) in enumerate(graph_setting_data):
            row = index // 4
            col = (index % 4) * 2

            lbl = QLabel(label)
            lbl.setProperty("html", True)
            graph_setting_layout.addWidget(lbl, row, col)

            input_field = QLineEdit()
            if placeholder:
                input_field.setPlaceholderText(placeholder)
            self.grid_inputs[key] = input_field
            graph_setting_layout.addWidget(input_field, row, col + 1)

        graph_setting_group.setLayout(graph_setting_layout)

        # 各グループをShow Axis Groupに追加
        show_axis_layout.addWidget(x_axis_group)
        show_axis_layout.addWidget(y_axis_group)
        show_axis_layout.addWidget(graph_setting_group)

        self.show_axis_group.setLayout(show_axis_layout)
        left_layout.addWidget(self.show_axis_group)


        # Z-Axis用のグループボックスを作成
        self.z_axis_group = QGroupBox("Show Colorbar")
        self.z_axis_group.setCheckable(True)
        self.z_axis_group.setChecked(False)
        self.z_axis_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        z_axis_layout = QVBoxLayout()  # 縦方向にレイアウト

        # group box の cheak box でテキストカラーを変更
        self.z_axis_group.toggled.connect(lambda: self.toggle_group_box_text_color(self.z_axis_group))

        # Z-Axisの設定データ
        z_axis_data = [
            ("Label :", "Z-Axis Label", "Intensity"),
            (", Unit :", "Z-Axis Unit", "a.u."),
            (", SI prefix :", "Z-Axis SI prefix", None),
            (", Tick Label :", "Z-Axis Tick Label", "-0.5, -0.25, 0, 0.25, 0.5")
        ]

        # Z-Axisの設定を配置するグリッド
        z_axis_grid_layout = QGridLayout()

        # Z-Axisオプション
        for index, (label, key, placeholder) in enumerate(z_axis_data):
            row = index // 4
            col = (index % 4) * 2

            lbl = QLabel(label)
            lbl.setProperty("html", True)
            z_axis_grid_layout.addWidget(lbl, row, col)

            if "prefix" in key:
                combo = QComboBox()
                combo.addItems(["Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da", "", "d", "c", "m", "μ", "n", "p", "f", "a", "z", "y"])
                combo.setCurrentText("")
                self.prefix_combos.append(combo)
                z_axis_grid_layout.addWidget(combo, row, col + 1)
            elif key == "":
                continue
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                if "Unit" in key:
                    input_field.setFixedWidth(unit_width)
                self.grid_inputs[key] = input_field
                z_axis_grid_layout.addWidget(input_field, row, col + 1)

        # Z-AxisのグリッドレイアウトをZ-Axisのメインレイアウトに追加
        z_axis_layout.addLayout(z_axis_grid_layout)
        
        # Colorbar Sizeレイアウト
        colorbar_grid_layout = QGridLayout()

        # Colorbar Size option data
        colorbar_grid_data = [
            ("Colorbar Width (inch) :", "Colorbar Width", "0.15"),
            (", Between Graph and Colorbar (inch) :", "Between Graph and Colorbar", "0.1"),
            (", Bottom :", "Colorbar Bottom", None)
        ]

        # Colorbar Size options
        for index, (label, key, placeholder) in enumerate(colorbar_grid_data):
            row = index // 3  # 行番号 (2列ごとに新しい行)
            col = (index % 3) * 2  # 列番号 (ラベルと入力を2つの列で占有)

            # Create label
            lbl = QLabel(label)
            lbl.setProperty("html", True)
            colorbar_grid_layout.addWidget(lbl, row, col)  # Add label to the grid

            if "Bottom" in key:
                checkbox = QCheckBox()
                self.grid_inputs[key] = checkbox
                colorbar_grid_layout.addWidget(checkbox, row, col + 1)
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                self.grid_inputs[key] = input_field
                colorbar_grid_layout.addWidget(input_field, row, col + 1)  # 入力フィールドを配置

        # Colorbar SizeのグリッドレイアウトをZ-Axisのメインレイアウトに追加
        z_axis_layout.addLayout(colorbar_grid_layout)

        # レイアウトをZ-Axisグループボックスに設定
        self.z_axis_group.setLayout(z_axis_layout)

        # メインレイアウトにZ-Axisグループボックスを追加
        left_layout.addWidget(self.z_axis_group)


        # Show Arrow用のグループボックスを作成
        self.show_arrow_group = QGroupBox("Show Arrows")
        self.show_arrow_group.setCheckable(True)
        self.show_arrow_group.setChecked(False)
        self.show_arrow_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        show_arrow_layout = QVBoxLayout()  # 縦方向にレイアウト

        # group box の cheak box でテキストカラーを変更
        self.show_arrow_group.toggled.connect(lambda: self.toggle_group_box_text_color(self.show_arrow_group))

        # Show Arrowの設定データ
        show_arrow_data = [
            ("Block Size :", "Block Size", "5"),
            (", Lnegth :", "Arrow Lnegth", "1.0"),
            (", Width :", "Arrow Width", "0.01"),
            (", Color :", "Arrow Color", "white")
        ]

        # Show Arrowの設定を配置するグリッド
        show_arrow_grid_layout = QGridLayout()

        # Show Arrowオプション
        for index, (label, key, placeholder) in enumerate(show_arrow_data):
            row = index // 4
            col = (index % 4) * 2

            lbl = QLabel(label)
            lbl.setProperty("html", True)
            show_arrow_grid_layout.addWidget(lbl, row, col)

            if "prefix" in key:
                combo = QComboBox()
                combo.addItems(["Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da", "", "d", "c", "m", "μ", "n", "p", "f", "a", "z", "y"])
                combo.setCurrentText("")
                self.prefix_combos.append(combo)
                show_arrow_grid_layout.addWidget(combo, row, col + 1)
            elif key == "":
                continue
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                if "Unit" in key:
                    input_field.setFixedWidth(unit_width)
                self.grid_inputs[key] = input_field
                show_arrow_grid_layout.addWidget(input_field, row, col + 1)

        show_arrow_layout.addLayout(show_arrow_grid_layout)
        self.show_arrow_group.setLayout(show_arrow_layout)
        left_layout.addWidget(self.show_arrow_group)

        

        # Save setting layout
        save_setting_grid_layout = QGridLayout()

        # Save setting data
        save_setting_grid_data = [
            ("Extension :", "Extension", None),
            (", dpi :", "dpi", "300"),
            (", GIF animation speed (ms) :", "GIF animation speed", "200")
        ]

        # Save setting
        for index, (label, key, placeholder) in enumerate(save_setting_grid_data):
            row = index // 3  # 行番号 (3列ごとに新しい行)
            col = (index % 3) * 2  # 列番号 (ラベルと入力を2つの列で占有)

            # Create label
            lbl = QLabel(label)
            lbl.setProperty("html", True)
            save_setting_grid_layout.addWidget(lbl, row, col)  # Add label to the grid

            if key in ["Extension"]:
                combo = QComboBox()
                combo.addItems(["png", "jpg", "svg", "eps", "pdf", "gif"])  # Extensionの選択肢を追加
                self.grid_inputs[key] = combo
                save_setting_grid_layout.addWidget(combo, row, col + 1)  # コンボボックスを配置
            else:
                input_field = QLineEdit()
                if placeholder:
                    input_field.setPlaceholderText(placeholder)
                self.grid_inputs[key] = input_field
                save_setting_grid_layout.addWidget(input_field, row, col + 1)  # 入力フィールドを配置

        # Add the Save setting layout to the main layout
        right_layout.addLayout(save_setting_grid_layout)


        # OVFファイル選択用レイアウトを追加
        ovf_file_layout = QHBoxLayout()

        # ラベルを作成
        ovf_file_label = QLabel("Displayed OVF File :")
        ovf_file_layout.addWidget(ovf_file_label)

        # OVFファイルコンボボックスを作成
        self.ovf_file_combo = QComboBox()
        self.ovf_file_combo.addItem("No OVF files found")  # 初期状態
        self.ovf_file_combo.setEnabled(False)  # ディレクトリが未設定の場合は無効化
        self.ovf_file_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ovf_file_layout.addWidget(self.ovf_file_combo)

        # レイアウトをメインレイアウトに追加
        right_layout.addLayout(ovf_file_layout)


        # Graph display area
        self.graph_display = QLabel()
        self.graph_display.setObjectName("graph_display")
        self.graph_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graph_display.setMinimumSize(int(800 * scale_factor), int(400 * scale_factor))
        right_layout.addWidget(self.graph_display)

        # Save & Load ボタンの追加
        save_load_layout = QHBoxLayout()  # ボタン用レイアウト
        # Saveボタン
        self.save_button = QPushButton("Save Conditions")
        self.save_button.clicked.connect(self.save_variables_to_json)
        save_load_layout.addWidget(self.save_button)
        # Loadボタン
        self.load_button = QPushButton("Load Conditions")
        self.load_button.clicked.connect(self.load_variables_from_json)
        save_load_layout.addWidget(self.load_button)
        # right_layout に追加
        right_layout.addLayout(save_load_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        self.check_button = QPushButton("Check")
        self.output_button = QPushButton("Output")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)  # 初期状態では無効化
        button_layout.addWidget(self.check_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.output_button)
        right_layout.addLayout(button_layout)
        self.check_button.clicked.connect(self.show_images)
        self.output_button.clicked.connect(self.save_images)
        self.cancel_button.clicked.connect(self.cancel_operation)

        self.cancel_event = threading.Event()  # 中断フラグ

        # Add the progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        footer_layout.addWidget(self.progress_bar)

        if footer_available:
            footer_widget, self.footer_label = fw.create_footer_widget(footer_font_color, footer_font_size, footer_background_color, scale_factor)
            footer_layout.addWidget(footer_widget)
        else:
            footer_widget = QWidget()
            footer_layout = QVBoxLayout(footer_widget)
            footer_layout.setContentsMargins(0, 0, 0, 0)
            footer_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {footer_background_color};
                    border-top: none;
                }}
            """)

            self.footer_label = QLabel("")
            self.footer_label.setAlignment(Qt.AlignCenter)
            self.footer_label.setStyleSheet(f"font-size: {footer_font_size}; font-family: {font_family}; color: {footer_font_color};")
            footer_widget.setFixedHeight(int(15 * scale_factor))
            footer_layout.addWidget(self.footer_label)

            # フッター領域をメインレイアウトに追加
            footer_layout.addWidget(footer_widget)
        
        # 左右のレイアウトをメインレイアウトに追加
        main_layout.addLayout(left_layout)
        main_layout.addSpacing(int(10 * scale_factor))
        main_layout.addLayout(right_layout) 

        layout.addLayout(main_layout)
        layout.addLayout(footer_layout)

        # メインレイアウトをウィンドウにセット
        main_widget.setLayout(main_layout)
        
        # initialize
        self.update_N(self.input_line.text())
        self.update_axis_options("Graph X-Axis")
        self.update_axis_options("Graph Y-Axis")
        self.update_axis_label()
        self.update_axis_unit()
        self.update_margin()
        self.update_graph_font_size()
        self.toggle_group_box_text_color(self.z_axis_group)
        self.toggle_group_box_text_color(self.show_axis_group)
        self.toggle_group_box_text_color(self.show_arrow_group)
        self.update_arrow()
        self.update_colormap(self.format_combo.currentText())

        if is_debug:
            self.update_output_format_options(self.get_first_ovf_file_header(self.input_line.text()))
            self.update_plane_index_options()
            self.update_ovf_file_combo(self.input_line.text())
            self.update_sixe()
            self.update_overall_range_by_size("x")
            self.update_overall_range_by_size("y")
            self.update_overall_range_by_size("z")

        # Connect singals for automatic updates
        self.input_line.editingFinished.connect(self.update_on_input_change)

        self.grid_inputs["Sizex"].editingFinished.connect(lambda: self.update_overall_range_by_size("x"))
        self.grid_inputs["Sizey"].editingFinished.connect(lambda: self.update_overall_range_by_size("y"))
        self.grid_inputs["Sizez"].editingFinished.connect(lambda: self.update_overall_range_by_size("z"))

        for i, combo in enumerate(self.axis_combos):
            if i == 0:
                combo.currentIndexChanged.connect(lambda: (self.update_axis_options("Graph X-Axis"), self.update_overall_range_by_graph_axis("X")))
            else:
                combo.currentIndexChanged.connect(lambda: (self.update_axis_options("Graph Y-Axis"), self.update_overall_range_by_graph_axis("Y")))
            combo.currentIndexChanged.connect(lambda: self.update_plane_index_options())
        
        self.format_combo.currentIndexChanged.connect(lambda: (self.update_colormap(self.format_combo.currentText())))
    
    def update_on_input_change(self):
        """Handles all updates triggered by changes in the input_line."""
        directory = self.input_line.text()
        self.update_N(directory)
        self.update_footer_by_input_line(directory)
        self.update_output_format_options(self.get_first_ovf_file_header(directory))
        self.update_plane_index_options()
        self.update_ovf_file_combo(directory)
    
    def update_footer_by_input_line(self, directory):
        ovf_file_path_arr = glob.glob(os.path.join(directory, "*.ovf")) if not len(directory) == 0 else []
        if ovf_file_path_arr:
            self.footer_label.setText(f"{len(ovf_file_path_arr)} OVF files found in the selected directory.")
        else:
            self.footer_label.setText("No OVF files found in the selected directory.")
    
    def get_first_ovf_file_header(self, directory):
        ovf_file_path_arr = glob.glob(os.path.join(directory, "*.ovf")) if not len(directory) == 0 else []
        header = {}
        if ovf_file_path_arr:
            try:
                # 最初の OVF ファイルのヘッダーを読み取る
                header = rof.read_ovf_file(ovf_file_path_arr[0], output_mode='headers')
            except Exception as e:
                print("Error reading OVF file:", e)
        print("get_first_ovf_file_header - header :", header)
        return header
    
    def update_N(self, directory):
        # OVF ファイルを取得
        ovf_file_path_arr = glob.glob(os.path.join(directory, "*.ovf")) if not len(directory) == 0 else []
        if ovf_file_path_arr:
            try:
                # 最初の OVF ファイルのヘッダーを読み取る
                headers = rof.read_ovf_file(ovf_file_path_arr[0], output_mode='headers')
                print("update_N - headers :", headers)

                # Nx, Ny, Nz に対応する値を設定
                self.grid_inputs["Nx"].setText(str(headers.get("xnodes", "")))
                self.grid_inputs["Ny"].setText(str(headers.get("ynodes", "")))
                self.grid_inputs["Nz"].setText(str(headers.get("znodes", "")))
            except Exception as e:
                print("Error reading OVF file:", e)

        else:
            self.grid_inputs["Nx"].setText("")
            self.grid_inputs["Ny"].setText("")
            self.grid_inputs["Nz"].setText("")
    
    def update_axis_options(self, changed_axis):
        """
        Updates the available options for Graph X-Axis and Graph Y-Axis
        to ensure they do not share the same value.
        """
        # Get current values
        x_axis_value = self.axis_combos[0].currentText()
        y_axis_value = self.axis_combos[1].currentText()

        # Available options
        options = ["x", "y", "z"]

        # Block signals to avoid infinite recursion
        self.axis_combos[0].blockSignals(True)
        self.axis_combos[1].blockSignals(True)

        try:
            if changed_axis == "Graph X-Axis":
                # Update Y-Axis options
                current_y_value = self.axis_combos[1].currentText()
                self.axis_combos[1].clear()  # Y-Axisの選択肢をリセット
                for option in options:
                    if option != x_axis_value:  # X-Axisの値を除外
                        self.axis_combos[1].addItem(option)
                if current_y_value in options and current_y_value != x_axis_value:
                    self.axis_combos[1].setCurrentText(current_y_value)
            elif changed_axis == "Graph Y-Axis":
                # Update X-Axis options
                current_x_value = self.axis_combos[0].currentText()
                self.axis_combos[0].clear()  # X-Axisの選択肢をリセット
                for option in options:
                    if option != y_axis_value:  # Y-Axisの値を除外
                        self.axis_combos[0].addItem(option)
                if current_x_value in options and current_x_value != y_axis_value:
                    self.axis_combos[0].setCurrentText(current_x_value)
        finally:
            # Restore signal handling
            self.axis_combos[0].blockSignals(False)
            self.axis_combos[1].blockSignals(False)
    
    def update_plane_index_options(self):
        """
        Updates the available options for Plane index based on Graph X-Axis and Graph Y-Axis.
        The Plane index corresponds to the axis not selected in Graph X-Axis and Graph Y-Axis,
        ranging from 0 to N-1 where N is the number of nodes along that axis.
        """

        current_plane_index = int(self.index_combo.currentText()) if self.index_combo.currentText().isdigit() else float('nan')

        # Get the currently selected axes
        x_axis = self.axis_combos[0].currentText()  # Graph X-Axis
        y_axis = self.axis_combos[1].currentText()  # Graph Y-Axis

        # Determine the unused axis
        all_axes = ["x", "y", "z"]
        unused_axis = next(axis for axis in all_axes if axis not in [x_axis, y_axis])

        # Determine the range for the unused axis
        if unused_axis == "x":
            max_index = int(self.grid_inputs["Nx"].text()) if self.grid_inputs["Nx"].text().isdigit() else 0
        elif unused_axis == "y":
            max_index = int(self.grid_inputs["Ny"].text()) if self.grid_inputs["Ny"].text().isdigit() else 0
        elif unused_axis == "z":
            max_index = int(self.grid_inputs["Nz"].text()) if self.grid_inputs["Nz"].text().isdigit() else 0
        else:
            max_index = 0  # Default fallback

        # Update the Plane index combo box
        self.index_combo.clear()
        self.index_combo.addItems([str(i) for i in range(max_index)])

        # Optionally, set a default value
        if current_plane_index < max_index:
            self.index_combo.setCurrentIndex(current_plane_index)
        elif max_index >= 0:
            self.index_combo.setCurrentIndex(0)
    
    def update_output_format_options(self, header):
        """
        Updates the available options for the Output Format combo box
        based on the provided value.

        Parameters:
        - value (int): Determines the available options for Output Format.
        """
        # Clear existing options
        self.format_combo.clear()

        try:
            valuedim = header["valuedim"]
        except KeyError:
            valuedim = None

        # Define options based on the value
        if valuedim == 3:
            options = ["m", "m_x", "m_y", "m_z"]
        elif valuedim == 1:
            try:
                option_item = header["valuelabels"]
            except KeyError:
                option_item = "any"
            options = [option_item]
        else:
            options = ["invalid"]  # Handle unexpected values (example)

        # Add new options to the combo box
        self.format_combo.addItems(options)

        # Set default selection
        self.format_combo.setCurrentText(options[0])

    def update_ovf_file_combo(self, directory):
        """
        Updates the OVF file combo box with the OVF files in the specified directory.

        Parameters:
        - directory (str): Path to the directory to search for OVF files.
        """
        # OVFファイルを取得
        ovf_file_paths = glob.glob(os.path.join(directory, "*.ovf"))

        # コンボボックスをリセット
        self.ovf_file_combo.clear()

        if ovf_file_paths:
            # ファイル名を取得してコンボボックスに追加
            ovf_file_names = [os.path.basename(path) for path in ovf_file_paths]
            self.ovf_file_combo.addItems(ovf_file_names)
            self.ovf_file_combo.setEnabled(True)  # コンボボックスを有効化
        else:
            # OVFファイルが見つからない場合
            self.ovf_file_combo.addItem("No OVF files found")
            self.ovf_file_combo.setEnabled(False)  # コンボボックスを無効化
    
    def update_axis_label(self):
        # Get the currently selected axes
        x_axis = self.axis_combos[0].currentText()  # Graph X-Axis
        y_axis = self.axis_combos[1].currentText()  # Graph Y-Axis

        self.grid_inputs["X-Axis Label"].setText(f"Position ${x_axis}$")
        self.grid_inputs["Y-Axis Label"].setText(f"Position ${y_axis}$")
        self.grid_inputs["Z-Axis Label"].setText("Intensity")
    
    def update_axis_unit(self):
        self.grid_inputs["X-Axis Unit"].setText("m")
        self.grid_inputs["Y-Axis Unit"].setText("m")
        self.grid_inputs["Z-Axis Unit"].setText("a.u.")
    
    def update_margin(self):
        self.grid_inputs["Left"].setText("0.7")
        self.grid_inputs["Top"].setText("0.5")
        self.grid_inputs["Right"].setText("0.7")
        self.grid_inputs["Bottom"].setText("0.5")
        self.grid_inputs["Colorbar Width"].setText("0.15")
        self.grid_inputs["Between Graph and Colorbar"].setText("0.1")
    
    def update_overall_range_by_size(self, changed_size_axis):
        graph_x_axis = self.axis_combos[0].currentText()
        graph_y_axis = self.axis_combos[1].currentText()
        set_axis = "X" if changed_size_axis == graph_x_axis else "Y"
        try:
            if changed_size_axis in (graph_x_axis, graph_y_axis):
                changed_size = float(self.grid_inputs["Size" + changed_size_axis].text())
                self.grid_inputs[set_axis + "-Axis Overall range min"].setText("0")
                self.grid_inputs[set_axis + "-Axis Overall range max"].setText(str(changed_size))
        except ValueError:
            self.grid_inputs[set_axis + "-Axis Overall range min"].setText("")
            self.grid_inputs[set_axis + "-Axis Overall range max"].setText("")
    
    def update_overall_range_by_graph_axis(self, changed_axis):
        try:
            combo_idx = {"X" : 0, "Y" : 1}[changed_axis]
            graph_axis = self.axis_combos[combo_idx].currentText()
            size = float(self.grid_inputs["Size" + graph_axis].text())
            self.grid_inputs[changed_axis + "-Axis Overall range min"].setText("0")
            self.grid_inputs[changed_axis + "-Axis Overall range max"].setText(str(size))
        except ValueError:
            self.grid_inputs[changed_axis + "-Axis Overall range min"].setText("")
            self.grid_inputs[changed_axis + "-Axis Overall range max"].setText("")
    
    def update_graph_font_size(self):
        self.grid_inputs["Label font size"].setText("11")
        self.grid_inputs["Label padding"].setText("4")
        self.grid_inputs["Tick label font size"].setText("10")
        self.grid_inputs["Tick label padding"].setText("4")
    
    def update_arrow(self):
        self.grid_inputs["Block Size"].setText("5")
        self.grid_inputs["Arrow Lnegth"].setText("1.0")
        self.grid_inputs["Arrow Width"].setText("0.01")
        self.grid_inputs["Arrow Color"].setText("white")

    def update_colormap(self, output_format, current_colormap_name=None):
        self.colormap_combo.clear()

        for colormap_name, base64_data in cs.colormap_data.items():
            if output_format and output_format[-1] in ["x", "y", "z"]:
                pass  
            elif colormap_name != "hsv":
                continue  

            pixmap = cs.colormapFromBase64(base64_data)
            icon = QIcon(pixmap)
            self.colormap_combo.addItem(icon, colormap_name)

        if current_colormap_name:
            self.colormap_combo.setCurrentText(current_colormap_name)
        
        # z_axis_groupの有効/無効を切り替え
        if output_format and output_format[-1] in ["x", "y", "z"]:
            # Show Colorbarの有効化
            self.z_axis_group.setEnabled(True)
            self.z_axis_group.setStyleSheet("QGroupBox::title { color: black; }")
            # Show Arrowsの無効化
            self.show_arrow_group.setChecked(False)
            self.show_arrow_group.setEnabled(False)  # 無効化
            self.show_arrow_group.setStyleSheet("QGroupBox::title { color: gray; }")
        else:
            # Show Colorbarの無効化
            self.z_axis_group.setChecked(False)
            self.z_axis_group.setEnabled(False)
            self.z_axis_group.setStyleSheet("QGroupBox::title { color: gray; }")
            # Show Arrowsの有効化
            self.show_arrow_group.setEnabled(True)   # 有効化
            self.show_arrow_group.setStyleSheet("QGroupBox::title { color: black; }")

    
    def validate_input(self, input_field, min_value):
        value = input_field.text()
        try:
            # 値が空または min_value 未満ならリセット
            if value == "" or float(value) < min_value:
                input_field.setText(f"{min_value:.2f}")  # 最小値にリセット
        except ValueError:
            # 入力が数値でない場合もリセット
            input_field.setText(f"{min_value:.2f}")
    
    def toggle_group_box_text_color(self, group_box):
        # Determine the text color based on the checked state
        text_color = "black" if group_box.isChecked() else "gray"
        border_color = self.checked_border_color if group_box.isChecked() else self.unchecked_border_color
        
        # Find all QLabel widgets inside the group box and update their color
        for label in group_box.findChildren(QLabel):
            label.setStyleSheet(f"color: {text_color};")
        
        for widget in group_box.findChildren((QLineEdit, QComboBox)):
            widget.setStyleSheet(f"border: {self.border_width} solid {border_color};")
        
        # Disable or enable other widgets inside the group box
        for widget in group_box.findChildren((QLineEdit, QComboBox, QCheckBox)):
            widget.setEnabled(group_box.isChecked())

    # debug
    def update_sixe(self):
        self.grid_inputs["Sizex"].setText("1280e-9")
        self.grid_inputs["Sizey"].setText("640e-9")
        self.grid_inputs["Sizez"].setText("5e-9")

    def browse_input(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.input_line.setText(directory)
            self.update_footer_by_input_line(directory)
            self.update_N(directory)
            self.update_output_format_options(self.get_first_ovf_file_header(directory))
            self.update_colormap(self.format_combo.currentText(), self.colormap_combo.currentText())
            self.update_plane_index_options()
            self.update_ovf_file_combo(directory)
    
    def cancel_operation(self):
        self.cancel_event.set()

    def save_variables_to_json(self):
        """変数をJSONファイルとして保存する"""
        variables = self.get_variables()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Conditions", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w') as file:
                    json.dump(variables, file, indent=4)
                self.footer_label.setText(f"Conditions saved to {file_path}")
            except Exception as e:
                self.footer_label.setText(f"Error saving Conditions: {str(e)}")

    def load_variables_from_json(self):
        """JSONファイルから変数を読み込み、UIに反映する"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Variables", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    variables = json.load(file)
                self.set_variables_to_ui(variables)
                self.footer_label.setText(f"Conditions loaded from {file_path}")
            except Exception as e:
                self.footer_label.setText(f"Error loading Conditions: {str(e)}")

    def set_variables_to_ui(self, variables):
        """読み込んだ変数をUIに反映する"""
        for key, value in variables.items():
            
            if value is None or key in ["Nx", "Ny", "Nz"]:  # Noneの場合はスキップ
                continue

            # print("set_variables_to_ui -  key, value:", key, value)

            if key in self.grid_inputs:
                widget = self.grid_inputs[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value)
            elif key == "Input Directory":
                self.input_line.setText(value)
                self.update_on_input_change()
            elif key == "Graph X-Axis":
                if value:
                    self.axis_combos[0].addItem(value)
                    self.axis_combos[0].setCurrentText(value)
                    self.update_axis_options("Graph X-Axis")
            elif key == "Graph Y-Axis":
                if value:
                    self.axis_combos[1].setCurrentText(value)
                    self.update_axis_options("Graph Y-Axis")
            elif key == "Plane index":
                if value is not None and str(value).isdigit():
                    self.index_combo.setCurrentText(str(value))
            elif key == "Output Format":
                self.format_combo.setCurrentText(str(value))
                self.update_colormap(self.format_combo.currentText())
            elif key == "Displayed OVF File":
                self.ovf_file_combo.setCurrentText(str(value))
            elif key == "X-Axis SI prefix":
                self.prefix_combos[0].setCurrentText(str(value))
            elif key == "Y-Axis SI prefix":
                self.prefix_combos[1].setCurrentText(str(value))
            elif key == "Z-Axis SI prefix":
                self.prefix_combos[2].setCurrentText(str(value))
            elif key == "Colormap":
                self.colormap_combo.setCurrentText(str(value))
            elif key == "Show Axis":
                self.show_axis_group.setChecked(value)
            elif key == "Show Arrows":
                self.show_arrow_group.setChecked(value)
            elif key == "Show Colorbar":
                self.z_axis_group.setChecked(value)
    
    
    @pyqtSlot()
    def disable_inputs(self):
        for widget in self.findChildren((QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox)):
            widget.setEnabled(False)
        # 中断ボタンを有効化
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setEnabled(True)

    @pyqtSlot()
    def enable_inputs(self):
        for widget in self.findChildren((QLineEdit, QPushButton, QComboBox, QCheckBox)):
            widget.setEnabled(True)
        for group_box in self.findChildren(QGroupBox):
            group_box.setEnabled(True)
            if isinstance(group_box, QGroupBox) and group_box.isCheckable():
                self.set_group_box_enabled(group_box, group_box.isChecked())
        
        self.update_colormap(self.format_combo.currentText(), self.colormap_combo.currentText())

        # 中断ボタンを無効化
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setEnabled(False)
    
    def set_group_box_enabled(self, group_box, state):
        for child in group_box.findChildren((QLineEdit, QComboBox, QCheckBox, QPushButton)):
            child.setEnabled(state)

    def get_variables(self):
        try:
            variables = {

                # int 型の変数
                "Nx": int(self.grid_inputs["Nx"].text()) if self.grid_inputs["Nx"].text().isdigit() else None,
                "Ny": int(self.grid_inputs["Ny"].text()) if self.grid_inputs["Ny"].text().isdigit() else None,
                "Nz": int(self.grid_inputs["Nz"].text()) if self.grid_inputs["Nz"].text().isdigit() else None,
                "Plane index": int(self.index_combo.currentText()) if self.index_combo.currentText().isdigit() else None,
                "Block Size": int(self.grid_inputs["Block Size"].text()) if self.grid_inputs["Block Size"].text().isdigit() else 5,
                "dpi": int(self.grid_inputs["dpi"].text()) if self.grid_inputs["dpi"].text().isdigit() else 300,

                # float 型の変数
                "Sizex": float(self.grid_inputs["Sizex"].text()) if self.grid_inputs["Sizex"].text() else None,
                "Sizey": float(self.grid_inputs["Sizey"].text()) if self.grid_inputs["Sizey"].text() else None,
                "Sizez": float(self.grid_inputs["Sizez"].text()) if self.grid_inputs["Sizez"].text() else None,
                "Left": float(self.grid_inputs["Left"].text()) if self.grid_inputs["Left"].text() else 0.7,
                "Top": float(self.grid_inputs["Top"].text()) if self.grid_inputs["Top"].text() else 0.5,
                "Right": float(self.grid_inputs["Right"].text()) if self.grid_inputs["Right"].text() else 0.7,
                "Bottom": float(self.grid_inputs["Bottom"].text()) if self.grid_inputs["Bottom"].text() else 0.5,
                "Colorbar Width": float(self.grid_inputs["Colorbar Width"].text()) if self.grid_inputs["Colorbar Width"].text() else float('nan'),
                "Between Graph and Colorbar": float(self.grid_inputs["Between Graph and Colorbar"].text()) if self.grid_inputs["Between Graph and Colorbar"].text() else float('nan'),
                "X-Axis Overall range min": float(self.grid_inputs["X-Axis Overall range min"].text()) if self.grid_inputs["X-Axis Overall range min"].text() else None,
                "X-Axis Overall range max": float(self.grid_inputs["X-Axis Overall range max"].text()) if self.grid_inputs["X-Axis Overall range max"].text() else None,
                "X-Axis Displayed range min": float(self.grid_inputs["X-Axis Displayed range min"].text()) if self.grid_inputs["X-Axis Displayed range min"].text() else None,
                "X-Axis Displayed range max": float(self.grid_inputs["X-Axis Displayed range max"].text()) if self.grid_inputs["X-Axis Displayed range max"].text() else None,
                "Y-Axis Overall range min": float(self.grid_inputs["Y-Axis Overall range min"].text()) if self.grid_inputs["Y-Axis Overall range min"].text() else None,
                "Y-Axis Overall range max": float(self.grid_inputs["Y-Axis Overall range max"].text()) if self.grid_inputs["Y-Axis Overall range max"].text() else None,
                "Y-Axis Displayed range min": float(self.grid_inputs["Y-Axis Displayed range min"].text()) if self.grid_inputs["Y-Axis Displayed range min"].text() else None,
                "Y-Axis Displayed range max": float(self.grid_inputs["Y-Axis Displayed range max"].text()) if self.grid_inputs["Y-Axis Displayed range max"].text() else None,
                "Z-Axis Displayed range min": float(self.grid_inputs["Z-Axis Displayed range min"].text()) if self.grid_inputs["Z-Axis Displayed range min"].text() else None,
                "Z-Axis Displayed range max": float(self.grid_inputs["Z-Axis Displayed range max"].text()) if self.grid_inputs["Z-Axis Displayed range max"].text() else None,
                "Aspect ratio width": float(self.grid_inputs["Aspect ratio width"].text()) if self.grid_inputs["Aspect ratio width"].text() else None,
                "Aspect ratio height": float(self.grid_inputs["Aspect ratio height"].text()) if self.grid_inputs["Aspect ratio height"].text() else None,
                "GIF animation speed": float(self.grid_inputs["GIF animation speed"].text()) if self.grid_inputs["GIF animation speed"].text() else 100.,
                "Label font size": float(self.grid_inputs["Label font size"].text()) if self.grid_inputs["Label font size"].text() else 11.,
                "Label padding": float(self.grid_inputs["Label padding"].text()) if self.grid_inputs["Label padding"].text() else 4.,
                "Tick label font size": float(self.grid_inputs["Tick label font size"].text()) if self.grid_inputs["Tick label font size"].text() else 10.,
                "Tick label padding": float(self.grid_inputs["Tick label padding"].text()) if self.grid_inputs["Tick label padding"].text() else 4.,
                "Arrow Lnegth": float(self.grid_inputs["Arrow Lnegth"].text()) if self.grid_inputs["Arrow Lnegth"].text() else 1.0,
                "Arrow Width": float(self.grid_inputs["Arrow Width"].text()) if self.grid_inputs["Arrow Width"].text() else 0.01,

                # str 型の変数
                "Input Directory": self.input_line.text(),
                "Output Format": self.format_combo.currentText(),
                "Graph X-Axis": self.axis_combos[0].currentText(),
                "Graph Y-Axis": self.axis_combos[1].currentText(),
                "Colormap": self.colormap_combo.currentText(),
                "Displayed OVF File": self.ovf_file_combo.currentText(),
                "X-Axis Label": self.grid_inputs["X-Axis Label"].text(),
                "X-Axis Unit": self.grid_inputs["X-Axis Unit"].text(),
                "X-Axis SI prefix": self.prefix_combos[0].currentText(),
                "Y-Axis Label": self.grid_inputs["Y-Axis Label"].text(),
                "Y-Axis Unit": self.grid_inputs["Y-Axis Unit"].text(),
                "Y-Axis SI prefix": self.prefix_combos[1].currentText(),
                "Z-Axis Label": self.grid_inputs["Z-Axis Label"].text(),
                "Z-Axis Unit": self.grid_inputs["Z-Axis Unit"].text(),
                "Z-Axis SI prefix": self.prefix_combos[2].currentText(),
                "Extension": self.grid_inputs["Extension"].currentText(),
                "X-Axis Tick Label": self.grid_inputs["X-Axis Tick Label"].text(),
                "Y-Axis Tick Label": self.grid_inputs["Y-Axis Tick Label"].text(),
                "Z-Axis Tick Label": self.grid_inputs["Z-Axis Tick Label"].text(),
                "Arrow Color": self.grid_inputs["Arrow Color"].text(),

                # bool 型の変数
                "Show Axis": self.show_axis_group.isChecked(),
                "Show Arrows": self.show_arrow_group.isChecked(),
                "Show Colorbar": self.z_axis_group.isChecked(),
                "is_Reverse": self.grid_inputs["is_Reverse"].isChecked(),"X-Axis Reverse": self.grid_inputs["X-Axis Reverse"].isChecked(),
                "Y-Axis Reverse": self.grid_inputs["Y-Axis Reverse"].isChecked(),
                "Colorbar Bottom": self.grid_inputs["Colorbar Bottom"].isChecked()
            }
        except ValueError:
            variables = {key: float('nan') for key in ["Nx", "Ny", "Nz", "Plane index", "Sizex", "Sizey", "Sizez"]}

        print("get_variables - variables :", variables)

        return variables

    def show_images(self):
        variables = self.get_variables()

        # ThreadPoolExecutorを利用して非同期処理を開始
        self.executor = ThreadPoolExecutor(max_workers=1)  # スレッド数1
        self.executor.submit(self.show_images_task, variables)

    def show_images_task(self, variables):
        QMetaObject.invokeMethod(self, "disable_inputs", Qt.QueuedConnection)
        
        try:
            ovf_file_path = os.path.join(variables["Input Directory"], variables["Displayed OVF File"])

            # OVFファイルの読み込み
            data, header = rof.read_ovf_file(ovf_file_path, output_mode='both')
            print("show_images - data.shape :", data.shape)

            # 配列の取得と処理
            array, arrow_azimuthal_angle_array, arrow_magnitude_xy_array = ga.get_array(data, header, variables)
            print("show_images - array.shape :", array.shape)

            output_format = variables["Output Format"]

            if output_format[-1] in ["x", "y", "z"]:
                if array.ndim != 2:
                    raise ValueError("Only 2D arrays are supported for display.")
            else:
                if array.ndim != 3:
                    raise ValueError("Only 3D arrays are supported for display.")

            # 画像生成
            scaled_pixmap = mi.make_image(self, array, variables, mode="check", arrow_azimuthal_angle_array=arrow_azimuthal_angle_array, arrow_magnitude_xy_array=arrow_magnitude_xy_array)
            # scaled_pixmap = mi.make_image(self, array, variables, mode="check")

            # 最大値と最小値を取得
            max_intensity = np.max(array)
            min_intensity = np.min(array)
            max_str = f"{max_intensity:.2e}"
            min_str = f"{min_intensity:.2e}"

            QMetaObject.invokeMethod(self.footer_label, "setText", Q_ARG(str, f"Maximum intensity: {max_str}, Minimum intensity: {min_str} in the selected file."))

            # QMetaObject.invokeMethod(self.graph_display, "setPixmap", scaled_pixmap)
            self.update_image_display(scaled_pixmap)

        except Exception as e:
            QMetaObject.invokeMethod(self.footer_label, f"Error: {str(e)}")
        finally:
            QMetaObject.invokeMethod(self, "enable_inputs", Qt.QueuedConnection)

    @pyqtSlot(object)
    def update_image_display(self, pixmap):
        if pixmap is not None:
            self.graph_display.setAlignment(Qt.AlignCenter)
            self.graph_display.setPixmap(pixmap)

    def save_images(self):
        variables = self.get_variables()

        # ThreadPoolExecutorを利用して非同期処理を開始
        self.executor = ThreadPoolExecutor(max_workers=1)  # スレッド数1
        self.executor.submit(self.save_images_task, variables)

    def save_images_task(self, variables):
        self.cancel_event.clear()  # 中断フラグをリセット
        QMetaObject.invokeMethod(self, "disable_inputs", Qt.QueuedConnection)
        QMetaObject.invokeMethod(self.progress_bar, "show", Qt.QueuedConnection)
        QMetaObject.invokeMethod(self.progress_bar, "setValue", Q_ARG(int, 0))

        ovf_file_path_arr = glob.glob(os.path.join(variables["Input Directory"], "*.ovf"))
        total_steps = len(ovf_file_path_arr)

        try:
            if variables["Extension"] == "gif":
                frames = []
                for step, ovf_file_path in enumerate(ovf_file_path_arr):
                    if self.cancel_event.is_set():  # 中断フラグを確認
                        raise RuntimeError("Operation canceled by the user.")
                    data, header = rof.read_ovf_file(ovf_file_path, output_mode='both')
                    array, arrow_azimuthal_angle_array, arrow_magnitude_xy_array = ga.get_array(data, header, variables)

                    output_format = variables["Output Format"]

                    if output_format[-1] in ["x", "y", "z"]:
                        if array.ndim != 2:
                            raise ValueError("Only 2D arrays are supported for display.")
                    else:
                        if array.ndim != 3:
                            raise ValueError("Only 3D arrays are supported for display.")

                    pixmap, scaled_pixmap = mi.make_image(self, array, variables, mode="animation", arrow_azimuthal_angle_array=arrow_azimuthal_angle_array, arrow_magnitude_xy_array=arrow_magnitude_xy_array)

                    frames.append(pixmap)

                    self.update_image_display(scaled_pixmap)

                    progress = int((step + 1) / total_steps * 90)
                    QMetaObject.invokeMethod(self.progress_bar, "setValue", Q_ARG(int, progress))

                # GIFアニメーションの生成
                mi.create_gif(self, frames, variables)
                QMetaObject.invokeMethod(self.footer_label, "setText", Q_ARG(str, f"GIF animation saved with {len(frames)} frames in the selected directory."))

                QMetaObject.invokeMethod(self.progress_bar, "setValue", Q_ARG(int, 100))
            else:
                for step, ovf_file_path in enumerate(ovf_file_path_arr):
                    if self.cancel_event.is_set():  # 中断フラグを確認
                        raise RuntimeError("Operation canceled by the user.")
                    data, header = rof.read_ovf_file(ovf_file_path, output_mode='both')
                    array, arrow_azimuthal_angle_array, arrow_magnitude_xy_array = ga.get_array(data, header, variables)

                    saved_name = os.path.splitext(os.path.basename(ovf_file_path))[0]

                    output_format = variables["Output Format"]

                    if output_format[-1] in ["x", "y", "z"]:
                        if array.ndim != 2:
                            raise ValueError("Only 2D arrays are supported for display.")
                    else:
                        if array.ndim != 3:
                            raise ValueError("Only 3D arrays are supported for display.")

                    scaled_pixmap = mi.make_image(self, array, variables, mode="save", saved_name=saved_name, arrow_azimuthal_angle_array=arrow_azimuthal_angle_array, arrow_magnitude_xy_array=arrow_magnitude_xy_array)

                    self.update_image_display(scaled_pixmap)

                    progress = int((step + 1) / total_steps * 100)
                    QMetaObject.invokeMethod(self.progress_bar, "setValue", Q_ARG(int, progress))

                QMetaObject.invokeMethod(self.footer_label, "setText", Q_ARG(str, f"{len(ovf_file_path_arr)} {variables['Extension'].upper()} files were saved in the selected directory."))
        except RuntimeError as e:
            QMetaObject.invokeMethod(self.footer_label, "setText", Q_ARG(str, str(e)))
        except Exception as e:
            QMetaObject.invokeMethod(self.footer_label, "setText", Q_ARG(str, f"Error: {str(e)}"))
        finally:
            # UIリセット
            QMetaObject.invokeMethod(self.progress_bar, "hide", Qt.QueuedConnection)
            QMetaObject.invokeMethod(self, "enable_inputs", Qt.QueuedConnection)

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(gi.iconFromBase64())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
