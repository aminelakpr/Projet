import sys
import requests
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QFrame, QLabel, QLineEdit, QPushButton, 
                             QStackedWidget, QFormLayout, QGroupBox, QComboBox, 
                             QDoubleSpinBox, QGraphicsDropShadowEffect, QGridLayout,
                             QDialog, QScrollArea)
from PyQt5.QtCore import QTimer, Qt, QPointF, QRectF, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QPolygonF
import pyqtgraph as pg

STYLE_PALETTE = {
    "base": "#050505", "sidebar": "#0d0d0d", "card": "#141414", "border": "#2a2a2a",
    "text": "#e0e0e0", "text_muted": "#7a7a7a", "white": "#ffffff", "teal": "#00e5ff",
    "teal_light": "#84ffff", "magenta": "#f50057", "magenta_light": "#ff5983",
    "warning": "#ff9100", "success": "#00e676", "danger": "#d50000", "dim": "#222222"
}

QSS_STYLESHEET = f"""
QMainWindow, QDialog {{ background-color: {STYLE_PALETTE['base']}; color: {STYLE_PALETTE['text']}; }}
QFrame#Sidebar {{ background-color: {STYLE_PALETTE['sidebar']}; border-right: 1px solid {STYLE_PALETTE['border']}; padding: 10px; }}
QLabel#SidebarLogo {{ color: {STYLE_PALETTE['magenta']}; font-size: 24px; font-weight: bold; margin-bottom: 20px; }}
QLabel#SidebarLabel {{ color: {STYLE_PALETTE['text_muted']}; font-size: 13px; font-weight: bold; padding: 5px 10px; margin-top: 20px; letter-spacing: 1px; }}
QPushButton#NavButton {{ background-color: transparent; color: {STYLE_PALETTE['text']}; border: none; padding: 12px 15px; border-radius: 6px; font-size: 14px; text-align: left; margin: 2px 0; }}
QPushButton#NavButton:hover {{ background-color: #222222; }}
QPushButton#NavButton:checked {{ background-color: #222222; color: {STYLE_PALETTE['teal']}; font-weight: bold; border-left: 3px solid {STYLE_PALETTE['teal']}; }}
QStackedWidget {{ padding: 10px; }}
QFrame#Card, QGroupBox {{ background-color: {STYLE_PALETTE['card']}; border: 1px solid {STYLE_PALETTE['border']}; border-radius: 10px; padding: 15px; margin-bottom: 10px; }}
QGroupBox {{ margin-top: 25px; color: {STYLE_PALETTE['teal_light']}; font-weight: bold; font-size: 14px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background-color: transparent; }}
QWidget#TransparentContainer {{ background-color: transparent; }}
QScrollBar:vertical {{ background: {STYLE_PALETTE['base']}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {STYLE_PALETTE['border']}; border-radius: 5px; }}
QLabel#SectionTitle {{ color: {STYLE_PALETTE['text']}; font-size: 22px; font-weight: bold; margin-bottom: 15px; }}
QLabel#MetricValue {{ color: {STYLE_PALETTE['text']}; font-size: 20px; font-weight: bold; }}
QLabel#MetricUnit {{ color: {STYLE_PALETTE['text_muted']}; font-size: 14px; }}
QLabel#LargeMetricValue {{ font-size: 42px; font-weight: bold; margin: 10px 0; }}
QLineEdit, QComboBox, QDoubleSpinBox {{ background-color: {STYLE_PALETTE['base']}; color: {STYLE_PALETTE['text']}; border: 1px solid {STYLE_PALETTE['border']}; padding: 10px; border-radius: 6px; font-size: 14px; }}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {STYLE_PALETTE['teal']}; }}
QLabel#FormLabel {{ color: {STYLE_PALETTE['text']}; font-size: 14px; }}
QPushButton#PrimaryButton {{ background-color: {STYLE_PALETTE['teal']}; color: #000000; border: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; font-size: 15px; }}
QPushButton#PrimaryButton:hover {{ background-color: {STYLE_PALETTE['teal_light']}; }}
QPushButton#SecondaryButton {{ background-color: {STYLE_PALETTE['sidebar']}; color: {STYLE_PALETTE['text']}; border: 1px solid {STYLE_PALETTE['border']}; padding: 10px 20px; border-radius: 6px; font-weight: bold; }}
QPushButton#SecondaryButton:hover {{ background-color: #222222; }}
QLabel#StatusDotGreen {{ background-color: {STYLE_PALETTE['success']}; border-radius: 5px; }}
QLabel#StatusDotRed {{ background-color: {STYLE_PALETTE['danger']}; border-radius: 5px; }}
"""

def apply_shadow(widget, blur=20, offset=(0, 4)):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(offset[0], offset[1])
    shadow.setColor(QColor(0, 0, 0, 150))
    widget.setGraphicsEffect(shadow)

class TelemetryWorker(QThread):
    data_received = pyqtSignal(dict)
    connection_error = pyqtSignal()

    def __init__(self, target_ip):
        super().__init__()
        self.target_ip = target_ip

    def run(self):
        try:
            clean_ip = self.target_ip.strip().replace("http://", "").replace("https://", "").replace("/", "")
            url = f"http://{clean_ip}/api/telemetry"
            
            response = requests.get(url, timeout=3.0) 
            
            if response.status_code == 200:
                self.data_received.emit(response.json())
            else:
                print(f"\n[Worker Error] Connected to ESP32, but it returned status code: {response.status_code}")
                self.connection_error.emit()
                
        except requests.exceptions.Timeout:
            print(f"\n[Worker Error] Timeout! The ESP32 at {clean_ip} took more than 3 seconds to respond.")
            self.connection_error.emit()
            
        except requests.exceptions.ConnectionError:
            print(f"\n[Worker Error] Connection Refused. The IP {clean_ip} is unreachable from this PC.")
            self.connection_error.emit()
            
        except Exception as e:
            print(f"\n[Worker Error] Critical failure during telemetry request: {e}")
            self.connection_error.emit()

class CircuitDiagramWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(240)
        self.vin = 0.0; self.vout = 0.0; self.iin = 0.0; self.iout = 0.0; self.is_on = False
        self.switch_closed = False; self.visual_freq_ticks = 15; self.tick_counter = 0
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.animate); self.anim_timer.start(16) 
        
    def update_data(self, vin, vout, iin, iout, is_on):
        self.vin = vin; self.vout = vout; self.iin = iin; self.iout = iout; self.is_on = is_on
        
    def animate(self):
        if self.is_on:
            self.tick_counter += 1
            if self.tick_counter >= self.visual_freq_ticks:
                self.switch_closed = not self.switch_closed
                self.tick_counter = 0
                self.update() 
        else:
            if self.switch_closed:
                self.switch_closed = False 
                self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width(); h = self.height()
        top_y = h // 2 - 30; bottom_y = h // 2 + 50
        spacing = min((w - 300) // 5, 130)
        start_x = (w - (spacing * 4)) // 2
        
        x0 = start_x; x1 = x0 + spacing; x2 = x1 + spacing; x3 = x2 + spacing; x4 = x3 + spacing
        
        pen_wire = QPen(QColor(STYLE_PALETTE['text_muted']), 3)
        pen_comp = QPen(QColor(STYLE_PALETTE['teal']), 3)
        pen_switch = QPen(QColor(STYLE_PALETTE['warning']) if self.switch_closed else QColor(STYLE_PALETTE['magenta']), 3)
        
        painter.setPen(pen_wire)
        painter.drawLine(x0, bottom_y, x4 + 30, bottom_y)
        
        painter.setBrush(QColor(STYLE_PALETTE['base']))
        painter.drawEllipse(x0-6, top_y-6, 12, 12); painter.drawEllipse(x0-6, bottom_y-6, 12, 12)
        painter.drawLine(x0, top_y, x1, top_y)
        
        painter.setPen(pen_switch)
        if self.switch_closed:
            painter.drawLine(x1, top_y, x2, top_y) 
        else:
            painter.drawLine(x1, top_y, x2-10, top_y-25) 
            
        painter.setBrush(QColor(STYLE_PALETTE['card']))
        painter.drawEllipse(x1-4, top_y-4, 8, 8); painter.drawEllipse(x2-4, top_y-4, 8, 8)
        
        painter.setPen(pen_wire)
        painter.drawLine(x2, top_y, x2+20, top_y); painter.drawLine(x2, top_y, x2, top_y+25)
        painter.setPen(pen_comp)
        painter.drawLine(x2-15, top_y+25, x2+15, top_y+25) 
        poly = QPolygonF([QPointF(x2, top_y+25), QPointF(x2-15, top_y+45), QPointF(x2+15, top_y+45)])
        painter.setBrush(QColor(STYLE_PALETTE['card']))
        painter.drawPolygon(poly) 
        painter.setPen(pen_wire)
        painter.drawLine(x2, top_y+45, x2, bottom_y)
        
        painter.setPen(pen_comp)
        painter.setBrush(Qt.NoBrush)
        w_L = (x3 - x2) - 40
        arc_w = w_L / 4
        for i in range(4):
            rect = QRectF(x2 + 20 + i*arc_w, top_y - arc_w/2, arc_w, arc_w)
            painter.drawArc(rect, 0, 180 * 16)
            
        painter.setPen(pen_wire)
        painter.drawLine(x3-20, top_y, x4 + 30, top_y); painter.drawLine(x3, top_y, x3, top_y+30)
        painter.setPen(pen_comp)
        painter.drawLine(x3-15, top_y+30, x3+15, top_y+30); painter.drawLine(x3-15, top_y+40, x3+15, top_y+40)
        painter.setPen(pen_wire)
        painter.drawLine(x3, top_y+40, x3, bottom_y)
        
        painter.setBrush(QColor(STYLE_PALETTE['base']))
        painter.drawEllipse(x4-6, top_y-6, 12, 12); painter.drawEllipse(x4-6, bottom_y-6, 12, 12)
        
        rx = x4 + 30; r_top = top_y + 15; r_bot = bottom_y - 15; step = (r_bot - r_top) / 4
        
        painter.setPen(pen_wire)
        painter.drawLine(rx, top_y, rx, r_top); painter.drawLine(rx, r_bot, rx, bottom_y)
        painter.setPen(pen_comp)
        painter.drawPolyline(QPointF(rx, r_top), QPointF(rx-10, r_top + step*0.5), QPointF(rx+10, r_top + step*1.5),
                             QPointF(rx-10, r_top + step*2.5), QPointF(rx+10, r_top + step*3.5), QPointF(rx, r_bot))

        font_main = QFont("Segoe UI", 12, QFont.Bold); font_sub = QFont("Segoe UI", 10)
        painter.setFont(font_main)
        painter.setPen(QColor(STYLE_PALETTE['teal_light']))
        painter.drawText(x0 - 50, top_y - 30, f"Vin: {self.vin:.2f} V")
        painter.setPen(QColor(STYLE_PALETTE['magenta_light']))
        painter.drawText(x4 - 30, top_y - 30, f"Vout: {self.vout:.2f} V")
        
        painter.setFont(font_sub); painter.setPen(QColor(STYLE_PALETTE['white']))
        painter.drawText(x0 + 10, top_y - 10, f"Iin: {self.iin:.2f} A ➔")
        painter.drawText(x4 - 40, top_y - 10, f"➔ Iout: {self.iout:.2f} A")
        
        resistor_val = "∞"
        if self.is_on and self.iout > 0.05:
            resistor_val = f"{(self.vout / self.iout):.1f}"
        painter.setPen(QColor(STYLE_PALETTE['warning']))
        painter.drawText(rx + 15, top_y + 45, f"R = {resistor_val} Ω")

        painter.setPen(QColor(STYLE_PALETTE['text_muted']))
        painter.drawText(x1 + 15, top_y - 45, "PWM")
        painter.drawText(x2 + 20, top_y - 25, "L")
        painter.drawText(x3 + 20, top_y + 40, "C")

class StyledMessageDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title); self.setFixedSize(350, 150); self.setStyleSheet(QSS_STYLESHEET)
        layout = QVBoxLayout(self)
        lbl_msg = QLabel(message); lbl_msg.setAlignment(Qt.AlignCenter); lbl_msg.setStyleSheet("font-size: 15px;")
        layout.addWidget(lbl_msg)
        btn_ok = QPushButton("OK", objectName="PrimaryButton")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok, 0, Qt.AlignCenter)

class AuthDialog(QDialog):
    def __init__(self, title="Authentication Required", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title); self.setFixedSize(350, 200); self.setStyleSheet(QSS_STYLESHEET)
        layout = QVBoxLayout(self)
        lbl = QLabel("Enter Admin Password:", objectName="FormLabel"); lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        self.pwd_input = QLineEdit(); self.pwd_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.pwd_input)
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel", objectName="SecondaryButton"); btn_cancel.clicked.connect(self.reject)
        self.btn_auth = QPushButton("Authenticate", objectName="PrimaryButton"); self.btn_auth.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel); btn_layout.addWidget(self.btn_auth)
        layout.addLayout(btn_layout)
        
    def get_password(self): return self.pwd_input.text()

class MetricCard(QFrame):
    def __init__(self, title, unit, parent=None):
        super().__init__(parent)
        self.setObjectName("Card"); self.setMinimumWidth(200)
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 25)
        title_label = QLabel(title); title_label.setObjectName("MetricUnit"); title_label.setAlignment(Qt.AlignCenter); title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        self.value_label = QLabel("0.00"); self.value_label.setObjectName("LargeMetricValue"); self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        unit_label = QLabel(unit); unit_label.setObjectName("MetricUnit"); unit_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(unit_label)
        apply_shadow(self)

    def set_value(self, value, format_str="{:.2f}"): self.value_label.setText(format_str.format(value))
    def set_style(self, color_key): self.value_label.setStyleSheet(f"color: {STYLE_PALETTE[color_key]};")

class ModernBuckDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buck Converter Control Center")
        self.resize(1250, 850); self.setMinimumSize(1000, 750)
        
        self.target_ip = "192.168.4.1"
        self.system_is_on = False
        self.connection_active = False
        
        self.max_history = 60 
        self.v_in_history = []; self.v_out_history = []; self.i_in_history = []; self.i_out_history = []
        self.p_in_history = []; self.p_out_history = []; self.eff_history = []; self.temp_history = []
        
        pg.setConfigOption('background', STYLE_PALETTE['card']); pg.setConfigOption('foreground', STYLE_PALETTE['text_muted']); pg.setConfigOptions(antialias=True) 
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        
        QApplication.setFont(QFont("Segoe UI", 10))
        self.setup_sidebar(); self.setup_content_pages(); self.apply_style()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_telemetry)
        self.timer.start(1000) 

    def setup_sidebar(self):
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(300)
        self.sidebar_layout = QVBoxLayout(self.sidebar); self.sidebar_layout.setContentsMargins(15, 25, 15, 20); self.sidebar_layout.setSpacing(0)
        self.main_layout.addWidget(self.sidebar)
        
        logo = QLabel("BUCK CONVERTER"); logo.setObjectName("SidebarLogo"); logo.setAlignment(Qt.AlignCenter); self.sidebar_layout.addWidget(logo)
        self.sidebar_layout.addWidget(QLabel("ANALYTICS", objectName="SidebarLabel"))
        
        self.btn_live = QPushButton("Live Dashboard", objectName="NavButton"); self.btn_live.setCheckable(True); self.btn_live.setChecked(True)
        self.btn_charts = QPushButton("Detailed Charts", objectName="NavButton"); self.btn_charts.setCheckable(True)
        self.sidebar_layout.addWidget(self.btn_live); self.sidebar_layout.addWidget(self.btn_charts)
        
        self.sidebar_layout.addWidget(QLabel("SYSTEM", objectName="SidebarLabel"))
        self.btn_network = QPushButton("Connectivity", objectName="NavButton"); self.btn_network.setCheckable(True)
        self.btn_control = QPushButton("Converter Settings", objectName="NavButton"); self.btn_control.setCheckable(True)
        self.sidebar_layout.addWidget(self.btn_network); self.sidebar_layout.addWidget(self.btn_control)
        
        self.nav_buttons = [self.btn_live, self.btn_charts, self.btn_network, self.btn_control]
        for btn in self.nav_buttons: btn.clicked.connect(self.navigate_to_page)

        self.sidebar_layout.addStretch()
        
        status_box = QFrame(); status_box.setStyleSheet(f"background-color: {STYLE_PALETTE['card']}; border-radius: 8px; padding: 10px;")
        status_layout = QVBoxLayout(status_box); status_layout.setSpacing(8)
        
        net_layout = QHBoxLayout()
        self.dot_conn = QLabel(); self.dot_conn.setFixedSize(10, 10); self.dot_conn.setObjectName("StatusDotRed")
        self.lbl_conn = QLabel("Disconnected")
        self.lbl_conn.setStyleSheet(f"color: {STYLE_PALETTE['text_muted']}; font-size: 12px;")
        net_layout.addWidget(self.dot_conn); net_layout.addWidget(self.lbl_conn); net_layout.addStretch(); status_layout.addLayout(net_layout)
        
        pwr_layout = QHBoxLayout()
        self.dot_pwr = QLabel(); self.dot_pwr.setFixedSize(10, 10); self.dot_pwr.setObjectName("StatusDotRed") 
        self.lbl_pwr = QLabel("System: OFF"); self.lbl_pwr.setStyleSheet(f"color: {STYLE_PALETTE['danger']}; font-weight: bold; font-size: 13px;")
        pwr_layout.addWidget(self.dot_pwr); pwr_layout.addWidget(self.lbl_pwr); pwr_layout.addStretch(); status_layout.addLayout(pwr_layout)
        
        self.sidebar_layout.addWidget(status_box)

    def create_dual_plot(self, title, y_label, y_max):
        plot = pg.PlotWidget()
        plot.setTitle(title, color=STYLE_PALETTE['text'], size='11pt')
        plot.setMouseEnabled(x=False, y=False); plot.showGrid(x=True, y=True, alpha=0.2)
        plot.setYRange(0, y_max, padding=0); plot.setXRange(-self.max_history, 0, padding=0)
        plot.setMinimumHeight(200)
        plot.getAxis('bottom').setTicks([[(0, 'Now'), (-30, '30s'), (-60, '1m')]]); plot.addLegend(offset=(10, 10))
        return plot

    def setup_content_pages(self):
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)
        
        self.page_live = QWidget(); live_layout = QVBoxLayout(self.page_live); live_layout.setContentsMargins(40, 40, 40, 40)
        live_layout.addWidget(QLabel("System Overview", objectName="SectionTitle"))
        
        card_layout = QHBoxLayout(); card_layout.setSpacing(20)
        self.card_p_in = MetricCard("Input Power", "Watts"); self.card_p_in.set_style("white") 
        self.card_p_out = MetricCard("Output Power", "Watts"); self.card_p_out.set_style("white") 
        self.card_eff = MetricCard("System Efficiency", "%"); self.card_eff.set_style("teal")
        self.card_temp = MetricCard("Hardware Temp", "°C"); self.card_temp.set_style("warning")
        
        card_layout.addWidget(self.card_p_in); card_layout.addWidget(self.card_p_out)
        card_layout.addWidget(self.card_eff); card_layout.addWidget(self.card_temp); live_layout.addLayout(card_layout)
        
        live_layout.addSpacing(15); self.schematic_widget = CircuitDiagramWidget(); apply_shadow(self.schematic_widget); live_layout.addWidget(self.schematic_widget); live_layout.addSpacing(15)
        
        metrics_frame = QFrame(); metrics_frame.setObjectName("Card"); apply_shadow(metrics_frame)
        metrics_grid = QGridLayout(metrics_frame); metrics_grid.setContentsMargins(30, 20, 30, 20); metrics_grid.setHorizontalSpacing(50); metrics_grid.setVerticalSpacing(15)
        
        def add_metric(row, col, label_text, color_key):
            lbl_title = QLabel(label_text, objectName="MetricUnit")
            lbl_value = QLabel("0.00", objectName="MetricValue"); lbl_value.setStyleSheet(f"color: {STYLE_PALETTE[color_key]}; font-size: 18px;")
            metrics_grid.addWidget(lbl_title, row, col, 1, 1, Qt.AlignRight | Qt.AlignVCenter); metrics_grid.addWidget(lbl_value, row, col+1, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
            return lbl_value

        self.lbl_vin = add_metric(0, 0, "Input Voltage:", "text"); self.lbl_iin = add_metric(1, 0, "Input Current:", "text")
        self.lbl_vout = add_metric(0, 2, "Output Voltage:", "magenta_light"); self.lbl_iout = add_metric(1, 2, "Output Current:", "teal_light")
        live_layout.addWidget(metrics_frame); live_layout.addStretch(); self.pages.addWidget(self.page_live)
        
        self.page_charts = QWidget(); charts_layout = QVBoxLayout(self.page_charts); charts_layout.setContentsMargins(25, 20, 25, 25)
        charts_layout.addWidget(QLabel("Complete Diagnostic Charts", objectName="SectionTitle"))
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); charts_container = QWidget(); charts_container.setObjectName("TransparentContainer")
        cc_layout = QVBoxLayout(charts_container); cc_layout.setSpacing(15)
        
        self.plot_p = self.create_dual_plot("Power Transfer (W)", "Watts", 60)
        self.curve_p_in = self.plot_p.plot(name="Input Power", pen=pg.mkPen(color=STYLE_PALETTE['text_muted'], width=2, style=Qt.DashLine)); self.curve_p_out = self.plot_p.plot(name="Output Power", pen=pg.mkPen(color=STYLE_PALETTE['warning'], width=2.5))
        self.plot_v = self.create_dual_plot("Voltage Step-Down (V)", "Volts", 30)
        self.curve_v_in = self.plot_v.plot(name="Input Voltage", pen=pg.mkPen(color=STYLE_PALETTE['text_muted'], width=2, style=Qt.DashLine)); self.curve_v_out = self.plot_v.plot(name="Output Voltage", pen=pg.mkPen(color=STYLE_PALETTE['magenta'], width=2.5))
        self.plot_i = self.create_dual_plot("Current Profile (A)", "Amps", 6)
        self.curve_i_in = self.plot_i.plot(name="Input Current", pen=pg.mkPen(color=STYLE_PALETTE['text_muted'], width=2, style=Qt.DashLine)); self.curve_i_out = self.plot_i.plot(name="Output Current", pen=pg.mkPen(color=STYLE_PALETTE['teal'], width=2.5))
        self.plot_sys = self.create_dual_plot("Thermals & Efficiency", "Value", 100)
        self.curve_eff = self.plot_sys.plot(name="Efficiency (%)", pen=pg.mkPen(color=STYLE_PALETTE['success'], width=2.5)); self.curve_temp = self.plot_sys.plot(name="Temperature (°C)", pen=pg.mkPen(color=STYLE_PALETTE['danger'], width=2.5))

        cc_layout.addWidget(self.plot_p); cc_layout.addWidget(self.plot_v); cc_layout.addWidget(self.plot_i); cc_layout.addWidget(self.plot_sys)
        scroll_area.setWidget(charts_container); charts_layout.addWidget(scroll_area); self.pages.addWidget(self.page_charts)

        self.page_network = QWidget()
        net_layout = QVBoxLayout(self.page_network)
        net_layout.setContentsMargins(30, 30, 30, 30)
        net_layout.addWidget(QLabel("Connectivity Configuration", objectName="SectionTitle"))
        
        def add_form_row(form, label, widget):
            lbl = QLabel(label, objectName="FormLabel")
            form.addRow(lbl, widget)

        target_group = QGroupBox("GUI Connection Target")
        target_layout = QVBoxLayout(target_group)
        target_h_layout = QHBoxLayout()
        target_h_layout.setSpacing(15)
        
        lbl_target = QLabel("ESP32 IP / Hostname:", objectName="FormLabel")
        self.ip_input = QLineEdit(self.target_ip)
        self.ip_input.setPlaceholderText("e.g., 192.168.4.1 or buck-cv.local")
        
        self.btn_connect = QPushButton("Connect / Refresh")
        self.btn_connect.setObjectName("SecondaryButton")
        self.btn_connect.setFixedSize(160, 40)
        self.btn_connect.clicked.connect(self.request_telemetry)
        
        target_h_layout.addWidget(lbl_target)
        target_h_layout.addWidget(self.ip_input)
        target_h_layout.addWidget(self.btn_connect)
        target_layout.addLayout(target_h_layout)
        
        wifi_group = QGroupBox("Local Network (Instruct ESP32 to connect to factory WiFi)")
        wifi_form = QFormLayout(wifi_group); wifi_form.setHorizontalSpacing(30); wifi_form.setVerticalSpacing(15)
        self.wifi_ssid = QLineEdit(); self.wifi_pass = QLineEdit(); self.wifi_pass.setEchoMode(QLineEdit.Password)
        add_form_row(wifi_form, "Target Wi-Fi SSID:", self.wifi_ssid); add_form_row(wifi_form, "Target Wi-Fi Password:", self.wifi_pass)
        
        mqtt_group = QGroupBox("Industry 4.0 (MQTT / Node-RED)")
        mqtt_form = QFormLayout(mqtt_group); mqtt_form.setHorizontalSpacing(30); mqtt_form.setVerticalSpacing(15)
        self.mqtt_broker = QLineEdit("192.168.1.100"); self.mqtt_port = QLineEdit("1883"); self.mqtt_topic = QLineEdit("factory/buck1/data")
        add_form_row(mqtt_form, "MQTT Broker IP:", self.mqtt_broker); add_form_row(mqtt_form, "Port:", self.mqtt_port); add_form_row(mqtt_form, "Base Topic:", self.mqtt_topic)
        
        save_btn = QPushButton(" Apply Configuration to ESP32", objectName="PrimaryButton")
        apply_shadow(save_btn, blur=10, offset=(0, 4))
        save_btn.clicked.connect(self.sync_network)
        net_layout.addWidget(target_group); net_layout.addWidget(wifi_group); net_layout.addWidget(mqtt_group); net_layout.addWidget(save_btn, 0, Qt.AlignRight); net_layout.addStretch()
        self.pages.addWidget(self.page_network)
        
        self.page_control = QWidget(); ctrl_layout = QVBoxLayout(self.page_control); ctrl_layout.setContentsMargins(30, 30, 30, 30)
        header_ctrl = QHBoxLayout(); header_ctrl.addWidget(QLabel("Buck Converter Parameters", objectName="SectionTitle")); header_ctrl.addStretch()
        
        self.btn_power_on = QPushButton("⏻ TURN ON"); self.btn_power_on.setFixedSize(140, 45); self.btn_power_on.clicked.connect(lambda: self.send_command("ON"))
        self.btn_power_off = QPushButton("⏻ TURN OFF"); self.btn_power_off.setFixedSize(140, 45); self.btn_power_off.clicked.connect(lambda: self.send_command("OFF"))
        header_ctrl.addWidget(self.btn_power_on); header_ctrl.addWidget(self.btn_power_off); ctrl_layout.addLayout(header_ctrl)
        
        scroll_ctrl = QScrollArea(); scroll_ctrl.setWidgetResizable(True); settings_container = QWidget(); settings_container.setObjectName("TransparentContainer")
        settings_layout = QVBoxLayout(settings_container); settings_layout.setSpacing(20)
        
        pid_group = QGroupBox("PID Controller Tuning")
        pid_form = QFormLayout(pid_group); pid_form.setHorizontalSpacing(30); pid_form.setVerticalSpacing(15)
        self.spin_kp = QDoubleSpinBox(); self.spin_kp.setValue(1.5); self.spin_kp.setSingleStep(0.1)
        self.spin_ki = QDoubleSpinBox(); self.spin_ki.setValue(0.1); self.spin_ki.setSingleStep(0.01)
        self.spin_kd = QDoubleSpinBox(); self.spin_kd.setValue(0.05); self.spin_kd.setSingleStep(0.01)
        add_form_row(pid_form, "Kp (Proportional):", self.spin_kp); add_form_row(pid_form, "Ki (Integral):", self.spin_ki); add_form_row(pid_form, "Kd (Derivative):", self.spin_kd)
        settings_layout.addWidget(pid_group)
        
        safety_group = QGroupBox("Target & Safety Limits")
        safety_form = QFormLayout(safety_group); safety_form.setHorizontalSpacing(30); safety_form.setVerticalSpacing(15)
        self.spin_target = QDoubleSpinBox(); self.spin_target.setSuffix(" V"); self.spin_target.setValue(12.0)
        add_form_row(safety_form, "Target Output Voltage:", self.spin_target)
        self.spin_under_v = QDoubleSpinBox(); self.spin_under_v.setSuffix(" V"); self.spin_under_v.setValue(10.0)
        self.combo_under = QComboBox(); self.combo_under.addItems(["Warning Only", "Warning + Poweroff"])
        add_form_row(safety_form, "Undervoltage Threshold:", self.spin_under_v); add_form_row(safety_form, "Undervoltage Action:", self.combo_under)
        self.spin_over_v = QDoubleSpinBox(); self.spin_over_v.setSuffix(" V"); self.spin_over_v.setValue(14.0)
        self.combo_over = QComboBox(); self.combo_over.addItems(["Warning Only", "Warning + Poweroff"])
        add_form_row(safety_form, "Overvoltage Threshold:", self.spin_over_v); add_form_row(safety_form, "Overvoltage Action:", self.combo_over)
        settings_layout.addWidget(safety_group)
        
        scroll_ctrl.setWidget(settings_container); ctrl_layout.addWidget(scroll_ctrl)
        sync_btn = QPushButton(" Sync Parameters to ESP32", objectName="PrimaryButton"); sync_btn.clicked.connect(self.sync_params)
        apply_shadow(sync_btn, blur=10, offset=(0, 4)); ctrl_layout.addWidget(sync_btn, 0, Qt.AlignRight)
        
        self.pages.addWidget(self.page_control)

    def navigate_to_page(self):
        btn = self.sender()
        for other_btn in self.nav_buttons: other_btn.setChecked(False)
        btn.setChecked(True); self.pages.setCurrentIndex(self.nav_buttons.index(btn))

    def request_telemetry(self):
        raw_ip = self.ip_input.text().strip()
        clean_ip = raw_ip.replace("http://", "").replace("https://", "").replace("/", "")
        self.target_ip = clean_ip
        
        if hasattr(self, 'worker') and self.worker.isRunning():
            return
            
        self.worker = TelemetryWorker(self.target_ip)
        self.worker.data_received.connect(self.handle_telemetry_data)
        self.worker.connection_error.connect(self.handle_telemetry_error)
        self.worker.start()

    def handle_telemetry_error(self):
        self.connection_active = False
        self.update_connection_ui()

    def handle_telemetry_data(self, data):
        self.connection_active = True
        self.update_connection_ui()
        
        vin = data.get("vin", 0.0)
        vout = data.get("vout", 0.0)
        iin = data.get("iin", 0.0)
        iout = data.get("iout", 0.0)
        p_in = data.get("pin", 0.0)
        p_out = data.get("pout", 0.0)
        efficiency = data.get("eff", 0.0)
        temp = data.get("temp", 0.0)
        self.system_is_on = data.get("state") == "ON"
        
        self.update_power_ui()
        self.schematic_widget.update_data(vin, vout, iin, iout, self.system_is_on)
        
        self.v_in_history.append(vin); self.v_out_history.append(vout)
        self.i_in_history.append(iin); self.i_out_history.append(iout)
        self.p_in_history.append(p_in); self.p_out_history.append(p_out)
        self.eff_history.append(efficiency); self.temp_history.append(temp)
        
        if len(self.v_in_history) > self.max_history:
            self.v_in_history.pop(0); self.v_out_history.pop(0); self.i_in_history.pop(0); self.i_out_history.pop(0)
            self.p_in_history.pop(0); self.p_out_history.pop(0); self.eff_history.pop(0); self.temp_history.pop(0)
            
        current_len = len(self.v_in_history)
        relative_time = list(range(-current_len + 1, 1))
        
        self.curve_p_in.setData(relative_time, self.p_in_history); self.curve_p_out.setData(relative_time, self.p_out_history)
        self.curve_v_in.setData(relative_time, self.v_in_history); self.curve_v_out.setData(relative_time, self.v_out_history)
        self.curve_i_in.setData(relative_time, self.i_in_history); self.curve_i_out.setData(relative_time, self.i_out_history)
        self.curve_eff.setData(relative_time, self.eff_history); self.curve_temp.setData(relative_time, self.temp_history)
        
        self.card_p_in.set_value(p_in); self.card_p_out.set_value(p_out)
        self.card_eff.set_value(efficiency, "{:.1f}"); self.card_temp.set_value(temp, "{:.1f}")
        
        self.lbl_vin.setText(f"{vin:.2f} V"); self.lbl_iin.setText(f"{iin:.2f} A")
        self.lbl_vout.setText(f"{vout:.2f} V"); self.lbl_iout.setText(f"{iout:.2f} A")

    def send_command(self, cmd):
        auth = AuthDialog(f"Auth Required to TURN {cmd}", self)
        if auth.exec_() == QDialog.Accepted:
            pwd = auth.get_password()
            payload = {"command": cmd, "password": pwd}
            try:
                resp = requests.post(f"http://{self.target_ip}/api/control", json=payload, timeout=2)
                if resp.status_code == 200:
                    StyledMessageDialog("Success", f"System turned {cmd}.", self).exec_()
                elif resp.status_code == 401:
                    StyledMessageDialog("Error", "Authentication Failed. Incorrect Password.", self).exec_()
                else:
                    StyledMessageDialog("Error", "Failed to apply command.", self).exec_()
            except Exception as e:
                StyledMessageDialog("Error", f"Connection Error: {str(e)}", self).exec_()

    def sync_params(self):
        auth = AuthDialog("Authentication Required to Sync", self)
        if auth.exec_() == QDialog.Accepted:
            pwd = auth.get_password()
            payload = {
                "password": pwd,
                "kp": self.spin_kp.value(), "ki": self.spin_ki.value(), "kd": self.spin_kd.value(),
                "target_v": self.spin_target.value(),
                "uv_limit": self.spin_under_v.value(), "ov_limit": self.spin_over_v.value()
            }
            try:
                resp = requests.post(f"http://{self.target_ip}/api/params", json=payload, timeout=2)
                if resp.status_code == 200:
                    StyledMessageDialog("Success", "Parameters successfully synced to ESP32.", self).exec_()
                else:
                    StyledMessageDialog("Error", "Auth Failed or Invalid Request.", self).exec_()
            except Exception as e:
                StyledMessageDialog("Error", f"Connection Error: {str(e)}", self).exec_()

    def sync_network(self):
        auth = AuthDialog("Authentication Required for Network Setup", self)
        if auth.exec_() == QDialog.Accepted:
            pwd = auth.get_password()
            payload = {
                "password": pwd,
                "ssid": self.wifi_ssid.text(), "pass": self.wifi_pass.text(),
                "mqtt_broker": self.mqtt_broker.text(), "mqtt_port": int(self.mqtt_port.text()), "mqtt_topic": self.mqtt_topic.text()
            }
            try:
                resp = requests.post(f"http://{self.target_ip}/api/network", json=payload, timeout=2)
                if resp.status_code == 200:
                    StyledMessageDialog("Success", "Network config sent! ESP32 will reboot.", self).exec_()
                else:
                    StyledMessageDialog("Error", "Auth Failed.", self).exec_()
            except Exception as e:
                StyledMessageDialog("Error", f"Connection Error: {str(e)}", self).exec_()

    def update_connection_ui(self):
        if self.connection_active:
            self.dot_conn.setObjectName("StatusDotGreen")
            self.lbl_conn.setText("ESP32 Connected")
            self.lbl_conn.setStyleSheet(f"color: {STYLE_PALETTE['success']}; font-size: 12px;")
        else:
            self.dot_conn.setObjectName("StatusDotRed")
            self.lbl_conn.setText("ESP32 Disconnected")
            self.lbl_conn.setStyleSheet(f"color: {STYLE_PALETTE['danger']}; font-size: 12px;")
        self.dot_conn.style().unpolish(self.dot_conn); self.dot_conn.style().polish(self.dot_conn)

    def update_power_ui(self):
        if self.system_is_on:
            self.btn_power_on.setStyleSheet(f"background-color: {STYLE_PALETTE['success']}; color: black; font-weight: bold; border-radius: 6px; font-size: 14px;")
            self.btn_power_off.setStyleSheet(f"background-color: {STYLE_PALETTE['dim']}; color: {STYLE_PALETTE['text_muted']}; border: 1px solid {STYLE_PALETTE['border']}; border-radius: 6px; font-size: 14px;")
            self.dot_pwr.setObjectName("StatusDotGreen")
            self.lbl_pwr.setText("System: ON")
            self.lbl_pwr.setStyleSheet(f"color: {STYLE_PALETTE['success']}; font-weight: bold; font-size: 13px;")
        else:
            self.btn_power_off.setStyleSheet(f"background-color: {STYLE_PALETTE['danger']}; color: white; font-weight: bold; border-radius: 6px; font-size: 14px;")
            self.btn_power_on.setStyleSheet(f"background-color: {STYLE_PALETTE['dim']}; color: {STYLE_PALETTE['text_muted']}; border: 1px solid {STYLE_PALETTE['border']}; border-radius: 6px; font-size: 14px;")
            self.dot_pwr.setObjectName("StatusDotRed")
            self.lbl_pwr.setText("System: OFF")
            self.lbl_pwr.setStyleSheet(f"color: {STYLE_PALETTE['danger']}; font-weight: bold; font-size: 13px;")
        self.dot_pwr.style().unpolish(self.dot_pwr); self.dot_pwr.style().polish(self.dot_pwr)

    def apply_style(self):
        axis_font = QFont("Segoe UI", 8)
        for plot in [self.plot_p, self.plot_v, self.plot_i, self.plot_sys]:
            plot.getAxis('bottom').setStyle(tickFont=axis_font); plot.getAxis('left').setStyle(tickFont=axis_font)
            plot.getAxis('bottom').setPen(STYLE_PALETTE['border']); plot.getAxis('left').setPen(STYLE_PALETTE['border'])
        self.setStyleSheet(QSS_STYLESHEET)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernBuckDashboard()
    window.show()
    sys.exit(app.exec_())
