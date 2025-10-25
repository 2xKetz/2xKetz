"""CS2 Launcher with advanced UI customization."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple

from PySide6 import QtCore, QtGui, QtWidgets


APP_NAME = "CS2 Dark Aether Launcher"
SETTINGS_PATH = Path.home() / ".cs2_dark_aether_settings.json"
STEAM_APP_ID = "730"


class AnimatedButton(QtWidgets.QPushButton):
    """Push button with hover glow animation."""

    def __init__(self, label: str, *, accent_color: QtGui.QColor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(label, parent=parent)
        self.accent_color = accent_color
        self._setup_style()
        self._effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self._effect.setBlurRadius(0)
        self._effect.setColor(self.accent_color)
        self._effect.setOffset(0)
        self.setGraphicsEffect(self._effect)

        self._animation = QtCore.QPropertyAnimation(self._effect, b"blurRadius", self)
        self._animation.setDuration(200)
        self._animation.setStartValue(0)
        self._animation.setEndValue(30)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def _setup_style(self) -> None:
        self.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(20, 20, 35, 200);
                color: #f5f5f5;
                border: 2px solid rgba(120, 120, 255, 120);
                border-radius: 10px;
                padding: 12px 22px;
                font-size: 16px;
                letter-spacing: 2px;
            }
            QPushButton:pressed {
                background-color: rgba(45, 45, 70, 220);
            }
            """
        )

    def enterEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802 - Qt API
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Forward)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802 - Qt API
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Backward)
        self._animation.start()
        super().leaveEvent(event)


class NeonFrame(QtWidgets.QFrame):
    """Stylized container with neon outline and adjustable bloom."""

    def __init__(self, *, accent_color: QtGui.QColor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent_color = accent_color
        self.setObjectName("neonFrame")
        self.setStyleSheet(
            f"""
            QFrame#neonFrame {{
                background: rgba(10, 10, 25, 200);
                border-radius: 18px;
                border: 1px solid rgba({accent_color.red()}, {accent_color.green()}, {accent_color.blue()}, 150);
            }}
            """
        )
        self._drop_shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self._drop_shadow.setBlurRadius(40)
        self._drop_shadow.setColor(self._accent_color)
        self._drop_shadow.setOffset(0)
        self.setGraphicsEffect(self._drop_shadow)

    def set_bloom_enabled(self, enabled: bool) -> None:
        self._drop_shadow.setEnabled(True)
        self._drop_shadow.setBlurRadius(55 if enabled else 15)
        if enabled:
            self._drop_shadow.setColor(self._accent_color)
        else:
            muted = QtGui.QColor(40, 40, 60, 180)
            self._drop_shadow.setColor(muted)


class ResolutionSelector(QtWidgets.QWidget):
    """Widget to choose resolution presets or custom values."""

    resolutionChanged = QtCore.Signal(int, int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._presets = [
            (1920, 1080),
            (2560, 1440),
            (3840, 2160),
            (1280, 720),
            (1280, 960),
            (1024, 768),
            (800, 600),
        ]
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)

        self.preset_box = QtWidgets.QComboBox()
        for width, height in self._presets:
            self.preset_box.addItem(f"{width} x {height}", (width, height))
        self.preset_box.addItem("Custom", None)
        self.preset_box.currentIndexChanged.connect(self._on_preset_changed)

        self.width_spin = QtWidgets.QSpinBox()
        self.height_spin = QtWidgets.QSpinBox()
        for spin in (self.width_spin, self.height_spin):
            spin.setRange(640, 7680)
            spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setAccelerated(True)
            spin.setFixedWidth(100)
            spin.valueChanged.connect(self._emit_resolution)

        layout.addWidget(QtWidgets.QLabel("Resolution"), 0, 0)
        layout.addWidget(self.preset_box, 0, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel("Width"), 1, 0)
        layout.addWidget(self.width_spin, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Height"), 1, 2)
        layout.addWidget(self.height_spin, 1, 3)

        # Initialize with first preset
        self._set_resolution(*self._presets[0])

    def _set_resolution(self, width: int, height: int) -> None:
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self._emit_resolution()

    def _emit_resolution(self) -> None:
        self.resolutionChanged.emit(self.width_spin.value(), self.height_spin.value())

    def _on_preset_changed(self, index: int) -> None:
        data = self.preset_box.itemData(index)
        if data is None:
            self.width_spin.setEnabled(True)
            self.height_spin.setEnabled(True)
            return
        width, height = data
        self._set_resolution(width, height)
        self.width_spin.setEnabled(False)
        self.height_spin.setEnabled(False)

    def get_resolution(self) -> Tuple[int, int]:
        return self.width_spin.value(), self.height_spin.value()

    def set_resolution(self, width: int, height: int) -> None:
        for i, preset in enumerate(self._presets):
            if preset == (width, height):
                self.preset_box.setCurrentIndex(i)
                return
        self.preset_box.setCurrentIndex(self.preset_box.count() - 1)
        self.width_spin.setEnabled(True)
        self.height_spin.setEnabled(True)
        self._set_resolution(width, height)


class ThemePreview(QtWidgets.QLabel):
    """Displays the current background image with zoom-on-hover."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(200, 110)
        self.setScaledContents(True)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                border-radius: 14px;
                border: 1px solid rgba(120, 120, 255, 80);
                background: rgba(30, 30, 50, 120);
                color: rgba(250, 250, 250, 180);
                font-size: 13px;
                letter-spacing: 1px;
            }
            """
        )
        self._pixmap: QtGui.QPixmap | None = None

    def set_image(self, image_path: Path | None) -> None:
        if image_path and image_path.exists():
            pixmap = QtGui.QPixmap(str(image_path)).scaled(
                self.width(),
                self.height(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(pixmap)
            self._pixmap = pixmap
            self.setText("")
        else:
            self.setPixmap(QtGui.QPixmap())
            self.setText("No Theme Selected")
            self._pixmap = None

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if self._pixmap:
            self.setPixmap(
                self._pixmap.scaled(
                    self.width(),
                    self.height(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )


class ScanlineOverlay(QtWidgets.QWidget):
    """Semi-transparent scanline effect overlay."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802 - Qt API
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        color = QtGui.QColor(120, 120, 200, 40)
        pen = QtGui.QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        step = 6
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)
        painter.end()


class LauncherWindow(QtWidgets.QMainWindow):
    launched = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(960, 600)
        self.setMinimumSize(820, 520)
        self.accent_color = QtGui.QColor(130, 120, 255)
        self.settings: Dict[str, object] = {}
        self.background_path: Path | None = None
        self._build_ui()
        self._apply_global_style()
        self._load_settings()

    # region UI Setup
    def _build_ui(self) -> None:
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(24)

        header_label = QtWidgets.QLabel("CS2 DARK AETHER")
        header_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet(
            """
            QLabel {
                font-size: 34px;
                font-weight: 700;
                letter-spacing: 10px;
                color: #d2d3ff;
            }
            """
        )
        main_layout.addWidget(header_label)

        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(24)
        main_layout.addLayout(content_layout, stretch=1)

        self.control_frame = NeonFrame(accent_color=self.accent_color)
        control_layout = QtWidgets.QVBoxLayout(self.control_frame)
        control_layout.setSpacing(16)
        control_layout.setContentsMargins(26, 26, 26, 26)

        self.resolution_selector = ResolutionSelector()
        self.window_mode_box = QtWidgets.QComboBox()
        self.window_mode_box.addItems(["Fullscreen", "Borderless", "Windowed"])

        refresh_layout = QtWidgets.QHBoxLayout()
        self.refresh_spin = QtWidgets.QSpinBox()
        self.refresh_spin.setRange(60, 1000)
        self.refresh_spin.setValue(240)
        self.refresh_spin.setSuffix(" Hz")
        refresh_layout.addWidget(QtWidgets.QLabel("Refresh"))
        refresh_layout.addWidget(self.refresh_spin)
        refresh_layout.addStretch()

        launch_options_label = QtWidgets.QLabel("Launch Options")
        launch_options_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #c8c9ff;")

        self.novid_checkbox = QtWidgets.QCheckBox("Skip Intro Videos (-novid)")
        self.high_priority_checkbox = QtWidgets.QCheckBox("High Priority (+mat_queue_mode 2)")
        self.console_checkbox = QtWidgets.QCheckBox("Enable Console (-console)")

        control_layout.addWidget(self.resolution_selector)
        control_layout.addWidget(QtWidgets.QLabel("Window Mode"))
        control_layout.addWidget(self.window_mode_box)
        control_layout.addLayout(refresh_layout)
        control_layout.addWidget(launch_options_label)
        control_layout.addWidget(self.novid_checkbox)
        control_layout.addWidget(self.high_priority_checkbox)
        control_layout.addWidget(self.console_checkbox)
        control_layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        self.launch_button = AnimatedButton("LAUNCH CS2", accent_color=self.accent_color)
        self.launch_button.clicked.connect(self._launch_cs2)

        self.cfg_button = AnimatedButton("OPEN CFG FOLDER", accent_color=self.accent_color)
        self.cfg_button.clicked.connect(self._open_cfg_folder)

        button_layout.addWidget(self.launch_button, stretch=3)
        button_layout.addWidget(self.cfg_button, stretch=2)
        control_layout.addLayout(button_layout)

        content_layout.addWidget(self.control_frame, stretch=2)

        self.theme_frame = NeonFrame(accent_color=self.accent_color)
        theme_layout = QtWidgets.QVBoxLayout(self.theme_frame)
        theme_layout.setContentsMargins(26, 26, 26, 26)
        theme_layout.setSpacing(16)

        theme_header = QtWidgets.QLabel("Theme & Atmosphere")
        theme_header.setStyleSheet("font-size: 18px; font-weight: 600; letter-spacing: 2px; color: #d7d7ff;")

        self.theme_preview = ThemePreview()
        theme_layout.addWidget(theme_header)
        theme_layout.addWidget(self.theme_preview)

        theme_controls_layout = QtWidgets.QVBoxLayout()
        self.select_background_button = AnimatedButton("CHOOSE BACKGROUND", accent_color=self.accent_color)
        self.select_background_button.clicked.connect(self._choose_background)

        self.reset_background_button = AnimatedButton("RESET THEME", accent_color=self.accent_color)
        self.reset_background_button.clicked.connect(self._reset_background)

        theme_controls_layout.addWidget(self.select_background_button)
        theme_controls_layout.addWidget(self.reset_background_button)

        # Atmosphere toggles
        self.bloom_checkbox = QtWidgets.QCheckBox("Bloom Lighting")
        self.scanline_checkbox = QtWidgets.QCheckBox("Retro Scanlines")
        self.particle_checkbox = QtWidgets.QCheckBox("Particle Drift")
        for checkbox in (self.bloom_checkbox, self.scanline_checkbox, self.particle_checkbox):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._sync_atmosphere_effects)

        theme_controls_layout.addWidget(self.bloom_checkbox)
        theme_controls_layout.addWidget(self.scanline_checkbox)
        theme_controls_layout.addWidget(self.particle_checkbox)

        theme_layout.addLayout(theme_controls_layout)
        theme_layout.addStretch()

        content_layout.addWidget(self.theme_frame, stretch=3)

        self.status_label = QtWidgets.QLabel("Ready to breach.")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #9fa0ff; font-size: 15px; letter-spacing: 2px;")
        main_layout.addWidget(self.status_label)

        self._init_ambient_effects(central_widget)
        self._sync_atmosphere_effects()

    def _apply_global_style(self) -> None:
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(4, 4, 12))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(230, 230, 250))
        self.setPalette(palette)

        self.setStyleSheet(
            """
            QWidget {
                font-family: 'Rajdhani', 'Montserrat', 'Segoe UI', sans-serif;
                color: #f7f7ff;
            }
            QComboBox, QSpinBox, QCheckBox {
                background: rgba(20, 20, 35, 160);
                border: 1px solid rgba(120, 120, 255, 80);
                border-radius: 8px;
                padding: 8px;
                selection-background-color: rgba(120, 120, 255, 140);
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(120, 120, 255, 150);
                background: rgba(10, 10, 30, 200);
            }
            QCheckBox::indicator:checked {
                background: rgba(170, 150, 255, 220);
                border: 1px solid rgba(220, 210, 255, 220);
            }
            QLabel {
                color: rgba(220, 220, 255, 200);
            }
            """
        )

    def _init_ambient_effects(self, central_widget: QtWidgets.QWidget) -> None:
        # Particle overlay
        self.scanline_overlay = ScanlineOverlay(central_widget)
        self.scanline_overlay.hide()

        self.particle_view = QtWidgets.QGraphicsView(central_widget)
        self.particle_view.setStyleSheet("background: transparent; border: none;")
        self.particle_view.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.particle_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.particle_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.particle_scene = QtWidgets.QGraphicsScene(self.particle_view)
        self.particle_view.setScene(self.particle_scene)
        self.particle_view.hide()
        self.particle_view.setGeometry(central_widget.rect())
        self.scanline_overlay.setGeometry(central_widget.rect())

        self._particle_timer = QtCore.QTimer(self)
        self._particle_timer.setInterval(700)
        self._particle_timer.timeout.connect(self._spawn_particle)

    def _sync_atmosphere_effects(self) -> None:
        bloom_enabled = self.bloom_checkbox.isChecked()
        self.control_frame.set_bloom_enabled(bloom_enabled)
        self.theme_frame.set_bloom_enabled(bloom_enabled)

        particles_enabled = self.particle_checkbox.isChecked()
        if particles_enabled:
            self.particle_view.setVisible(True)
            if not self._particle_timer.isActive():
                self._particle_timer.start(700)
            self.particle_view.raise_()
        else:
            self.particle_view.setVisible(False)
            self._particle_timer.stop()
            self.particle_scene.clear()

        scanlines_enabled = self.scanline_checkbox.isChecked()
        self.scanline_overlay.setVisible(scanlines_enabled)
        if scanlines_enabled:
            self.scanline_overlay.raise_()

    # endregion

    # region Settings persistence
    def _load_settings(self) -> None:
        if SETTINGS_PATH.exists():
            try:
                self.settings = json.loads(SETTINGS_PATH.read_text())
            except json.JSONDecodeError:
                self.settings = {}
        else:
            self.settings = {}

        width = int(self.settings.get("width", 1920))
        height = int(self.settings.get("height", 1080))
        refresh = int(self.settings.get("refresh", 240))
        window_mode = self.settings.get("window_mode", "Fullscreen")
        background = self.settings.get("background" )
        novid = bool(self.settings.get("novid", True))
        high_priority = bool(self.settings.get("high_priority", False))
        console = bool(self.settings.get("console", False))
        bloom = bool(self.settings.get("bloom", True))
        scanline = bool(self.settings.get("scanline", True))
        particle = bool(self.settings.get("particle", True))

        self.resolution_selector.set_resolution(width, height)
        self.refresh_spin.setValue(refresh)
        idx = self.window_mode_box.findText(window_mode)
        self.window_mode_box.setCurrentIndex(max(idx, 0))
        self.novid_checkbox.setChecked(novid)
        self.high_priority_checkbox.setChecked(high_priority)
        self.console_checkbox.setChecked(console)
        self.bloom_checkbox.setChecked(bloom)
        self.scanline_checkbox.setChecked(scanline)
        self.particle_checkbox.setChecked(particle)

        self.background_path = Path(background) if background else None
        self.theme_preview.set_image(self.background_path)
        self._update_background_style()
        self._sync_atmosphere_effects()

    def _save_settings(self) -> None:
        width, height = self.resolution_selector.get_resolution()
        data = {
            "width": width,
            "height": height,
            "refresh": self.refresh_spin.value(),
            "window_mode": self.window_mode_box.currentText(),
            "background": str(self.background_path) if self.background_path else "",
            "novid": self.novid_checkbox.isChecked(),
            "high_priority": self.high_priority_checkbox.isChecked(),
            "console": self.console_checkbox.isChecked(),
            "bloom": self.bloom_checkbox.isChecked(),
            "scanline": self.scanline_checkbox.isChecked(),
            "particle": self.particle_checkbox.isChecked(),
        }
        SETTINGS_PATH.write_text(json.dumps(data, indent=2))

    # endregion

    # region Actions
    def _choose_background(self) -> None:
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp)")
        file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        if file_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selection = file_dialog.selectedFiles()
            if selection:
                self.background_path = Path(selection[0])
                self.theme_preview.set_image(self.background_path)
                self._update_background_style()
                self._save_settings()
                self._set_status("Theme locked in.")

    def _reset_background(self) -> None:
        self.background_path = None
        self.theme_preview.set_image(None)
        self._update_background_style()
        self._save_settings()
        self._set_status("Theme reset to default darkness.")

    def _update_background_style(self) -> None:
        if self.background_path and self.background_path.exists():
            self.centralWidget().setStyleSheet(
                f"background-image: url('{self.background_path.as_posix()}');"
                "background-position: center;"
                "background-repeat: no-repeat;"
                "background-size: cover;"
                ""
            )
        else:
            self.centralWidget().setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                " stop:0 #04040e, stop:0.5 #10102a, stop:1 #04040e);"
            )

    def _launch_cs2(self) -> None:
        width, height = self.resolution_selector.get_resolution()
        refresh = self.refresh_spin.value()
        window_mode_flag = {
            "Fullscreen": "-fullscreen",
            "Borderless": "-windowed -noborder",
            "Windowed": "-windowed",
        }.get(self.window_mode_box.currentText(), "-fullscreen")

        commands = [
            "-novid" if self.novid_checkbox.isChecked() else "",
            "-console" if self.console_checkbox.isChecked() else "",
            f"-w {width}",
            f"-h {height}",
            f"-refresh {refresh}",
            window_mode_flag,
            "+mat_queue_mode 2" if self.high_priority_checkbox.isChecked() else "",
        ]

        steam_cmd = self._detect_steam_command()
        if not steam_cmd:
            QtWidgets.QMessageBox.critical(self, "Steam Not Found", "Unable to locate the Steam executable.")
            return

        try:
            launch_list = [steam_cmd, "-applaunch", STEAM_APP_ID]
            for arg in commands:
                if arg:
                    launch_list.extend(arg.split())
            subprocess.Popen(launch_list)
            self._set_status("Deploying CS2 with your specs.")
            self._save_settings()
            self.launched.emit()
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "Launch Failed", f"Failed to launch CS2: {exc}")
            self._set_status("Launch failed. Check settings.")

    def _open_cfg_folder(self) -> None:
        cfg_path = self._get_cfg_path()
        if not cfg_path.exists():
            cfg_path.mkdir(parents=True, exist_ok=True)

        if platform.system() == "Windows":
            os.startfile(str(cfg_path))  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(cfg_path)])
        else:
            subprocess.Popen(["xdg-open", str(cfg_path)])
        self._set_status("CFG vault opened.")

    # endregion

    # region Helpers
    def _detect_steam_command(self) -> str | None:
        if platform.system() == "Windows":
            possible_paths = [
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Steam" / "steam.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Steam" / "steam.exe",
            ]
            for path in possible_paths:
                if path.exists():
                    return str(path)
            if path := shutil.which("steam.exe"):
                return path
            return None
        if platform.system() == "Darwin":
            mac_path = Path("/Applications/Steam.app/Contents/MacOS/steam_osx")
            if mac_path.exists():
                return str(mac_path)
            return shutil.which("steam")
        return shutil.which("steam")

    def _get_cfg_path(self) -> Path:
        if platform.system() == "Windows":
            return Path(os.environ.get("USERPROFILE", Path.home())) / "Saved Games" / "Counter-Strike 2" / "cfg"
        if platform.system() == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Counter-Strike 2" / "game" / "csgo" / "cfg"
        return Path.home() / ".local" / "share" / "Steam" / "steamapps" / "common" / "Counter-Strike Global Offensive" / "game" / "csgo" / "cfg"

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)
        effect = QtWidgets.QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(effect)
        animation = QtCore.QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(900)
        animation.setStartValue(0.3)
        animation.setEndValue(1.0)
        animation.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _spawn_particle(self) -> None:
        if not self.particle_checkbox.isChecked():
            return

        color = QtGui.QColor(self.accent_color)
        color.setAlpha(120)
        size = QtCore.QSizeF(6, 6)
        ellipse = self.particle_scene.addEllipse(QtCore.QRectF(QtCore.QPointF(0, 0), size), brush=QtGui.QBrush(color))

        area = self.centralWidget().rect()
        min_x = area.width() * 0.2
        span = max(int(area.width() * 0.6), 1)
        start_x = min_x + QtCore.QRandomGenerator.global_().bounded(span)
        start_y = area.height()
        ellipse.setPos(start_x, start_y)

        animation = QtCore.QPropertyAnimation(ellipse, b"pos")
        animation.setDuration(6000)
        animation.setStartValue(QtCore.QPointF(start_x, start_y))
        animation.setEndValue(QtCore.QPointF(start_x, -50))
        animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutQuad)
        animation.finished.connect(lambda: self.particle_scene.removeItem(ellipse))
        animation.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if hasattr(self, "particle_view"):
            self.particle_view.setGeometry(self.centralWidget().rect())
            self.particle_view.setSceneRect(QtCore.QRectF(self.centralWidget().rect()))
        if hasattr(self, "scanline_overlay"):
            self.scanline_overlay.setGeometry(self.centralWidget().rect())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802 - Qt API
        self._save_settings()
        super().closeEvent(event)

    # endregion


def run() -> int:
    QtWidgets.QApplication.setAttribute(QtCore.Qt.WidgetAttribute.AA_UseHighDpiPixmaps)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = LauncherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
