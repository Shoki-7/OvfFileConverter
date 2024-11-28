import sys
import ctypes
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QGridLayout, QFileDialog
)
from PyQt5.QtCore import Qt


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
        button_background_color = "#0078d7"
        button_hover_color = "#005a9e"
        graph_background_color = "#f5f5f5"
        border_radius = f"{int(5 * scale_factor)}px"
        border_width = f"{int(1 * scale_factor)}px"
        padding_value = f"{int(5 * scale_factor)}px"
        button_padding = f"{int(5 * scale_factor)}px {int(10 * scale_factor)}px"
        font_family = "Arial"

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
        self.input_line = QLineEdit()
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
            "<i>N<sub>x</sub></i>",
            "<i>N<sub>y</sub></i>",
            "<i>N<sub>z</sub></i>",
            "Size<i><sub>x</sub></i> (m)",
            "Size<i><sub>y</sub></i> (m)",
            "Size<i><sub>z</sub></i> (m)"
        ]
        self.grid_inputs = {}
        for i, label in enumerate(labels):
            lbl = QLabel(label + " :")
            lbl.setProperty("html", True)  # For custom styling if needed
            input_field = QLineEdit()
            # input_field.setPlaceholderText(f"Enter {label}")
            self.grid_inputs[label] = input_field
            grid_layout.addWidget(lbl, i // 3, (i % 3) * 2)
            grid_layout.addWidget(input_field, i // 3, (i % 3) * 2 + 1)
        layout.addLayout(grid_layout)

        # Output format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mx", "my", "mz", "all"])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Graph axis selection
        axis_layout = QGridLayout()
        axis_labels = ["Graph X-Axis:", "Graph Y-Axis:"]
        self.axis_combos = []
        for i, label in enumerate(axis_labels):
            lbl = QLabel(label)
            combo = QComboBox()
            combo.addItems(["x", "y", "z"])
            combo.currentIndexChanged.connect(self.check_axis_conflict)
            self.axis_combos.append(combo)
            axis_layout.addWidget(lbl, i, 0)
            axis_layout.addWidget(combo, i, 1)
        layout.addLayout(axis_layout)

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

        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Directory:")
        self.output_line = QLineEdit()
        output_browse = QPushButton("Browse")
        output_browse.setFixedSize(int(80 * scale_factor), int(30 * scale_factor))
        output_browse.clicked.connect(self.browse_output)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_browse)
        layout.addLayout(output_layout)

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

    def browse_input(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.input_line.setText(directory)

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_line.setText(directory)

    def check_axis_conflict(self):
        if self.axis_combos[0].currentText() == self.axis_combos[1].currentText():
            self.axis_combos[1].setStyleSheet("border: 1px solid red;")
        else:
            self.axis_combos[1].setStyleSheet("")
    
    def print_variables(self):
        print("Input Directory:", self.input_line.text())
        print("Grid Inputs:")
        for label, input_field in self.grid_inputs.items():
            print(f"  {label}: {input_field.text()}")
        print("Output Format:", self.format_combo.currentText())
        print("Graph X-Axis:", self.axis_combos[0].currentText())
        print("Graph Y-Axis:", self.axis_combos[1].currentText())
        print("Output Plane:", self.plane_line.text())
        print("Show Axis:", self.axis_check.isChecked())
        
        print("Show Arrows:", self.arrow_check.isChecked())
        print("Output Directory:", self.output_line.text())


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
