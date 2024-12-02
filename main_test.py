import sys
import ctypes
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QGridLayout, QFileDialog
)
from PyQt5.QtCore import Qt
import read_ovf_files as rof
import os
import glob

import numpy as np
from PyQt5.QtGui import QImage, QPixmap
import matplotlib.pyplot as plt
from io import BytesIO

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
        window_width = int(1000 * scale_factor)
        window_height = int(800 * scale_factor)

        self.setWindowTitle("Spin Wave Visualization Tool")
        self.setGeometry(100, 100, window_width, window_height)

        # Set the style sheet for the main window
        font_size = f"{int(14 * scale_factor)}px"
        label_color = "#333333"
        background_color = "#ffffff"
        input_border_color = "#cccccc"
        self.conflict_border_color = "red"
        button_background_color = "#0078d7"
        button_hover_color = "#005a9e"
        graph_background_color = "#f5f5f5"
        border_radius = f"{int(5 * scale_factor)}px"
        border_width = f"{int(1 * scale_factor)}px"
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
                border: {border_width} solid {input_border_color};
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
                border: {border_width} solid {input_border_color};
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
            QLabel#graph_display {{
                background-color: {graph_background_color};
                border: {border_width} solid {input_border_color};
            }}
        """)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Input path (directory only)
        input_layout = QHBoxLayout()
        input_label = QLabel("Input Directory:")
        # self.input_line = QLineEdit()
        self.input_line = QLineEdit(os.path.join(os.getcwd(), "TestOvfFiles"))
        input_browse = QPushButton("Browse")
        input_browse.setFixedSize(int(80 * scale_factor), int(30 * scale_factor))
        input_browse.clicked.connect(self.browse_input)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(input_browse)
        layout.addLayout(input_layout)

        # Grid size inputs with HTML-styled labels
        grid_layout = QGridLayout()
        labels = [
            ("<i>N<sub>x</sub></i>:", "Size<i><sub>x</sub></i> (m):", "Output Format:"),
            ("<i>N<sub>y</sub></i>:", "Size<i><sub>y</sub></i> (m):", "Graph X-Axis:"),
            ("<i>N<sub>z</sub></i>:", "Size<i><sub>z</sub></i> (m):", "Graph Y-Axis:")
        ]
        grid_inputs = [
            ("Nx", "Sizex", "Output Format"),
            ("Ny", "Sizey", "Graph X-Axis"),
            ("Nz", "Sizez", "Graph Y-Axis")
        ]

        # 入力フィールドとコンボボックスの作成
        self.grid_inputs = {}
        self.axis_combos = []
        for row, (label1, label2, label3) in enumerate(labels):
            # 最初の列
            lbl1 = QLabel(label1)
            lbl1.setProperty("html", True)
            input_field1 = QLineEdit()
            self.grid_inputs[grid_inputs[row][0]] = input_field1
            grid_layout.addWidget(lbl1, row, 0)
            grid_layout.addWidget(input_field1, row, 1)

            # 真ん中の列
            lbl2 = QLabel(label2)
            lbl2.setProperty("html", True)
            input_field2 = QLineEdit()
            self.grid_inputs[grid_inputs[row][1]] = input_field2
            grid_layout.addWidget(lbl2, row, 2)
            grid_layout.addWidget(input_field2, row, 3)

            # 最後の列
            lbl3 = QLabel(label3)
            combo = QComboBox()
            if grid_inputs[row][2] == "Output Format":
                combo.addItems(["mx", "my", "mz", "all"])
                self.format_combo = combo
            else:
                combo.addItems(["x", "y", "z"])
                self.axis_combos.append(combo)

                combo.currentIndexChanged.connect(self.check_axis_conflict)
            grid_layout.addWidget(lbl3, row, 4)
            grid_layout.addWidget(combo, row, 5)

        layout.addLayout(grid_layout)

        # Output plane
        plane_layout = QHBoxLayout()
        plane_label = QLabel("Output Plane (int):")
        self.plane_line = QLineEdit()
        plane_layout.addWidget(plane_label)
        plane_layout.addWidget(self.plane_line)
        layout.addLayout(plane_layout)

        # Display options
        options_layout = QHBoxLayout()
        self.axis_check = QCheckBox("Show Axis")
        self.arrow_check = QCheckBox("Show Arrows")
        options_layout.addWidget(self.axis_check)
        options_layout.addWidget(self.arrow_check)
        layout.addLayout(options_layout)

        # Graph display area
        self.graph_display = QLabel()
        self.graph_display.setObjectName("graph_display")
        self.graph_display.setFixedSize(int(800 * scale_factor), int(400 * scale_factor))
        layout.addWidget(self.graph_display, alignment=Qt.AlignCenter)

        # Action buttons
        button_layout = QHBoxLayout()
        self.check_button = QPushButton("Check")
        self.output_button = QPushButton("Output")
        button_layout.addWidget(self.check_button)
        button_layout.addWidget(self.output_button)
        layout.addLayout(button_layout)
        self.output_button.clicked.connect(self.print_variables)

        if footer_available:
            footer_widget, self.footer_label = fw.create_footer_widget(footer_font_color, footer_font_size, footer_background_color, scale_factor)
            layout.addWidget(footer_widget)
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
            layout.addWidget(footer_widget)
        
        # initialize
        self.update_N(self.input_line.text())

        # Connect singals for automatic updates
        self.input_line.editingFinished.connect(lambda: (self.update_N(self.input_line.text())))
    
    def update_N(self, directory):
        # OVF ファイルを取得
        ovf_file_path_arr = glob.glob(os.path.join(directory, "*.ovf")) if not len(directory) == 0 else []
        if ovf_file_path_arr:
            self.footer_label.setText(f"{len(ovf_file_path_arr)} OVF files found in the selected directory.")
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
            self.footer_label.setText("No OVF files found in the selected directory.")
            self.grid_inputs["Nx"].setText("")
            self.grid_inputs["Ny"].setText("")
            self.grid_inputs["Nz"].setText("")

    def browse_input(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.input_line.setText(directory)
            self.update_N(directory)
            
    def check_axis_conflict(self):
        if len(self.axis_combos) < 2:
            return
        if self.axis_combos[0].currentText() == self.axis_combos[1].currentText():
            self.axis_combos[1].setStyleSheet(f"border: {self.conflict_border_width} solid {self.conflict_border_color};")
        else:
            self.axis_combos[1].setStyleSheet("")

    def get_variables(self):
        try:
            variables = {
                # int 型の変数
                "Nx": int(self.grid_inputs["Nx"].text()) if self.grid_inputs["Nx"].text().isdigit() else float('nan'),
                "Ny": int(self.grid_inputs["Ny"].text()) if self.grid_inputs["Ny"].text().isdigit() else float('nan'),
                "Nz": int(self.grid_inputs["Nz"].text()) if self.grid_inputs["Nz"].text().isdigit() else float('nan'),
                "Output Plane": int(self.plane_line.text()) if self.plane_line.text().isdigit() else float('nan'),

                # float 型の変数
                "Sizex": float(self.grid_inputs["Sizex"].text()) if self.grid_inputs["Sizex"].text() else float('nan'),
                "Sizey": float(self.grid_inputs["Sizey"].text()) if self.grid_inputs["Sizey"].text() else float('nan'),
                "Sizez": float(self.grid_inputs["Sizez"].text()) if self.grid_inputs["Sizez"].text() else float('nan'),

                # str 型の変数
                "Input Directory": self.input_line.text(),
                "Output Format": self.format_combo.currentText(),
                "Graph X-Axis": self.axis_combos[0].currentText(),
                "Graph Y-Axis": self.axis_combos[1].currentText(),

                # bool 型の変数
                "Show Axis": self.axis_check.isChecked(),
                "Show Arrows": self.arrow_check.isChecked(),
            }
        except ValueError:
            variables = {key: float('nan') for key in ["Nx", "Ny", "Nz", "Output Plane", "Sizex", "Sizey", "Sizez"]}
        return variables

    def display_array_as_image(self, array):
        """Convert a 2D array to an image and display it on graph_display."""
        if array.ndim != 2:
            raise ValueError("Only 2D arrays are supported for display.")

        # # 正規化: 画像データを0～255にスケール変換
        # normalized_array = 255 * (array - np.min(array)) / (np.max(array) - np.min(array))
        # normalized_array = normalized_array.astype(np.uint8)

        # # NumPy 配列を QImage に変換
        # height, width = normalized_array.shape
        # image = QImage(normalized_array, width, height, QImage.Format_Grayscale8)

        # # QImage を QPixmap に変換
        # pixmap = QPixmap.fromImage(image)

        # # QLabel (graph_display) のサイズに合わせてリサイズ
        # label_width = self.graph_display.width()
        # label_height = self.graph_display.height()
        # scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # self.graph_display.setPixmap(scaled_pixmap)

        # Matplotlib を使って画像を作成
        fig, ax = plt.subplots()
        cax = ax.imshow(array, cmap="viridis", aspect="auto")
        fig.colorbar(cax, ax=ax)
        ax.set_xlabel("X-axis")
        ax.set_ylabel("Y-axis")

        # MatplotlibのプロットをQPixmapに変換
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue(), "PNG")

        # QLabel (graph_display) のサイズに合わせてリサイズ
        label_width = self.graph_display.width()
        label_height = self.graph_display.height()
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # QPixmap を QLabel に表示
        self.graph_display.setPixmap(scaled_pixmap)
    
    def print_variables(self):
        variables = self.get_variables()

        # 辞書を整形してコンソールに出力
        print("Variables:")
        for key, value in variables.items():
            print(f"  {key}: {value}")


        # Get a list of all OVF files in the directory
        ovf_file_path_arr = glob.glob(os.path.join(variables["Input Directory"], "*.ovf"))

        data, _ = rof.read_ovf_file(ovf_file_path_arr[0], output_mode='both')
        print("Data shape:", data.shape)

        array = data[0, :, :, 0]

        # 関数を呼び出して画像を表示
        self.display_array_as_image(array)

        return

        # Process each OVF file
        for ovf_file_path in ovf_file_path_arr:
            # Read the data and headers from the OVF file
            data, headers = rof.read_ovf_file(ovf_file_path)
            
            # Print headers and data shape
            print("Headers:", headers)
            print("Data shape:", data.shape)
            
            # Access and print a specific data point
            try:
                print("Data at [0, 5, 450]:", data[0, 5, 450])
            except IndexError:
                print("Index out of range for data array in file:", ovf_file_path)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
