
import time
from scipy import integrate, signal
from mne.time_frequency import psd_array_multitaper
from brainflow import DataFilter, FilterTypes
import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QComboBox,
    QCheckBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QGridLayout,
    QButtonGroup,
    QRadioButton,
    QGroupBox
)
NUM_ELECTRODES = 8
EEG_BANDS = [
    [0, 4],  # Delta
    [4, 7],  # Theta
    [7, 12],  # Alpha
    [12, 30],  # Beta
    [30, 50]  # Gamma
]

# Enables user to capture and compare the bandpower of two recording sessions
class ABBandpowerWidget(QWidget):

    def __init__(self, parent):

        # ** CLASS VARIABLE INITIALIZATION ** #

        super().__init__()
        self.parent = parent

        # Data gathering variables
        self.a_record_time = 0
        self.b_record_time = 0
        self.a_data = None
        self.b_data = None

        # Data processing variables
        self.filter_sixty_hz = False
        self.filter_zero_to_five_hz = False
        self.include_all_frequencies = True
        self.custom_low_frequency = 0
        self.custom_high_frequency = 125

        self.bp_methods = ["Welch's", "Multitaper", "FFT"]
        self.selected_bp_method = self.bp_methods[0]
        self.welch_window_length_fraction_of_total = 0.1

        self.include_all_electrodes = True
        self.custom_electrode_selection = []

        self.relative_plot = False

        # Processed data variables
        self.a_processed_bp = None
        self.b_processed_bp = None
        self.a_frequencies = [0, 0]
        self.b_frequencies = [0, 0]

        self.a_standard_band_values = [0, 0, 0, 0, 0]
        self.b_standard_band_values = [0, 0, 0, 0, 0]

        # ** WIDGET CONSTRUCTION ** #

        # ############# #
        # Input Section #
        # ############# #

        # State A #

        a_record_time_label = QLabel("State A Record Time (s): ")
        a_record_time_label.setStyleSheet("""color: #fff; font-size: 15px;""")

        a_record_time_input = QLineEdit()
        a_record_time_input.setPlaceholderText("0")
        a_record_time_input.setMaxLength(2)
        a_record_time_input.textChanged.connect(self.set_a_record_time)
        a_record_time_input.setStyleSheet("""background-color: #fff; color: #000;font: 15px; min-width: 30px;
                                             margin-bottom: 0px;  padding: 5px; max-width: 30px;""")

        self.a_record_button = QPushButton("Record State A")
        self.a_record_button.pressed.connect(self.pressed_record_a)
        self.a_record_button.released.connect(self.record_a)
        self.a_record_button.setStyleSheet("""
            border-image: none !important;
            border-style: outset;
            border-width: 2px;
            border-radius: 10px;
            border-color: beige;
            color: #fff;
            font-size: 15px;
        """)

        state_a = QHBoxLayout()
        state_a.addWidget(a_record_time_label)
        state_a.addWidget(a_record_time_input)
        state_a.addWidget(self.a_record_button)

        # State B #

        b_record_time_label = QLabel("State B Record Time (s): ")
        b_record_time_label.setStyleSheet("""color: #fff; font-size: 15px;""")

        b_record_time_input = QLineEdit()
        b_record_time_input.setPlaceholderText("0")
        b_record_time_input.setMaxLength(2)
        b_record_time_input.textChanged.connect(self.set_b_record_time)
        b_record_time_input.setStyleSheet("""background-color: #fff; color: #000;font: 15px; min-width: 30px;
                                             margin-bottom: 0px; max-width: 30px; padding: 5px;""")

        self.b_record_button = QPushButton("Record State B")
        self.b_record_button.pressed.connect(self.record_b_pressed)
        self.b_record_button.released.connect(self.record_b)
        self.b_record_button.setStyleSheet("""
            border-image: none !important;
            border-style: outset;
            border-width: 2px;
            border-radius: 10px;
            border-color: beige;
            color: #fff;
            font-size: 15px;
        """)

        state_b = QHBoxLayout()
        state_b.addWidget(b_record_time_label)
        state_b.addWidget(b_record_time_input)
        state_b.addWidget(self.b_record_button)

        # Bandpower Selection #

        bp_label = QLabel("Bandpower processing method: ")
        bp_label.setStyleSheet("""color: #fff; font-size: 15px;""")

        bp_method_list = QComboBox()
        bp_method_list.addItems(self.bp_methods)
        bp_method_list.setCurrentIndex(0)
        bp_method_list.setStyleSheet("""background-color: gray; color: #fff; min-width: 50px; max-width: 150px;""")
        bp_method_list.currentIndexChanged.connect(self.set_bp_method)

        bandpower_selection = QHBoxLayout()
        bandpower_selection.addWidget(bp_label)
        bandpower_selection.addWidget(bp_method_list)

        # Relative Plot Selection #

        relative_plot_checkbox = QCheckBox("Relative plot")
        relative_plot_checkbox.setStyleSheet("""color: #fff; font-size: 15px;""")
        relative_plot_checkbox.stateChanged.connect(self.set_relative_plot)

        # 60 Hz Filter Selection #

        sixty_hz_filter_checkbox = QCheckBox("Filter 60 Hz")
        sixty_hz_filter_checkbox.setStyleSheet("""color: #fff; font-size: 15px;""")
        sixty_hz_filter_checkbox.stateChanged.connect(self.set_sixty_hz_filter)

        # 0-5 Hz Filter Selection #

        zero_to_five_hz_filter_checkbox = QCheckBox("Filter 0-5 Hz")
        zero_to_five_hz_filter_checkbox.setStyleSheet("""color: #fff; font-size: 15px;""")
        zero_to_five_hz_filter_checkbox.stateChanged.connect(self.set_zero_to_five_hz_filter)

        # Frequency Range Selection #

        # Build all frequencies option
        all_frequencies_button = QRadioButton("Include all frequencies")
        all_frequencies_button.setStyleSheet("""color: #fff; font-size: 15px;""")
        all_frequencies_button.setChecked(True)

        # Build custom frequencies option
        custom_frequencies_button = QRadioButton("Custom frequency range")
        custom_frequencies_button.setStyleSheet("""color: #fff; font-size: 15px;""")

        custom_frequencies_low = QLineEdit()
        custom_frequencies_low.setPlaceholderText("0")
        custom_frequencies_low.setMaxLength(3)
        custom_frequencies_low.textChanged.connect(self.set_low_frequency)
        custom_frequencies_low.setStyleSheet("""background-color: #fff; color: #000;font: 15px; min-width: 50px;
                                                 margin-bottom: 0px; max-width: 50px; padding: 5px;""")
        custom_frequencies_high = QLineEdit()
        custom_frequencies_high.setPlaceholderText("125")
        custom_frequencies_high.setMaxLength(3)
        custom_frequencies_high.textChanged.connect(self.set_high_frequency)
        custom_frequencies_high.setStyleSheet("""background-color: #fff; color: #000;font: 15px; min-width: 50px;
                                                     margin-bottom: 0px; max-width: 50px; padding: 5px;""")

        custom_frequencies_option = QHBoxLayout()
        custom_frequencies_option.addWidget(custom_frequencies_button)
        custom_frequencies_option.addWidget(custom_frequencies_low)
        custom_frequencies_option.addWidget(custom_frequencies_high)

        self.frequency_selection = QButtonGroup()
        self.frequency_selection.addButton(all_frequencies_button)
        self.frequency_selection.addButton(custom_frequencies_button)
        self.frequency_selection.setId(all_frequencies_button, 1)
        self.frequency_selection.setId(custom_frequencies_button, 2)
        self.frequency_selection.idPressed.connect(self.toggle_custom_frequency)

        custom_frequencies_label = QLabel("Set custom frequency range")
        custom_frequencies_label.setStyleSheet("""color: #fff; font-size: 15px;""")

        # Build frequency range selection
        frequency_range_selection = QVBoxLayout()
        frequency_range_selection.addWidget(all_frequencies_button)
        frequency_range_selection.addLayout(custom_frequencies_option)

        # Included Electrode Selection #

        # Build all electrodes option
        all_electrodes_button = QRadioButton("Include all electrodes")
        all_electrodes_button.setStyleSheet("""color: #fff; font-size: 15px;""")
        all_electrodes_button.setChecked(True)

        # Build custom electrodes option
        custom_electrodes_button = QRadioButton("Include custom electrodes")
        custom_electrodes_button.setStyleSheet("""color: #fff; font-size: 15px;""")

        electrode_1_button = QCheckBox("1")
        electrode_2_button = QCheckBox("2")
        electrode_3_button = QCheckBox("3")
        electrode_4_button = QCheckBox("4")
        electrode_5_button = QCheckBox("5")
        electrode_6_button = QCheckBox("6")
        electrode_7_button = QCheckBox("7")
        electrode_8_button = QCheckBox("8")

        self.selected_electrodes_group = QButtonGroup()
        self.selected_electrodes_group.addButton(electrode_1_button)
        self.selected_electrodes_group.addButton(electrode_2_button)
        self.selected_electrodes_group.addButton(electrode_3_button)
        self.selected_electrodes_group.addButton(electrode_4_button)
        self.selected_electrodes_group.addButton(electrode_5_button)
        self.selected_electrodes_group.addButton(electrode_6_button)
        self.selected_electrodes_group.addButton(electrode_7_button)
        self.selected_electrodes_group.addButton(electrode_8_button)
        self.selected_electrodes_group.setId(electrode_1_button, 1)
        self.selected_electrodes_group.setId(electrode_2_button, 2)
        self.selected_electrodes_group.setId(electrode_3_button, 3)
        self.selected_electrodes_group.setId(electrode_4_button, 4)
        self.selected_electrodes_group.setId(electrode_5_button, 5)
        self.selected_electrodes_group.setId(electrode_6_button, 6)
        self.selected_electrodes_group.setId(electrode_7_button, 7)
        self.selected_electrodes_group.setId(electrode_8_button, 8)
        self.selected_electrodes_group.idPressed.connect(self.select_custom_electrode)
        self.selected_electrodes_group.setExclusive(False)

        electrode_1_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_2_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_3_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_4_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_5_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_6_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_7_button.setStyleSheet("""color: #fff;font-size: 15px;""")
        electrode_8_button.setStyleSheet("""color: #fff;font-size: 15px;""")

        custom_electrode_selection = QHBoxLayout()
        custom_electrode_selection.addWidget(electrode_1_button)
        custom_electrode_selection.addWidget(electrode_2_button)
        custom_electrode_selection.addWidget(electrode_3_button)
        custom_electrode_selection.addWidget(electrode_4_button)
        custom_electrode_selection.addWidget(electrode_5_button)
        custom_electrode_selection.addWidget(electrode_6_button)
        custom_electrode_selection.addWidget(electrode_7_button)
        custom_electrode_selection.addWidget(electrode_8_button)

        custom_electrodes_option = QVBoxLayout()
        custom_electrodes_option.addWidget(custom_electrodes_button)
        custom_electrodes_option.addLayout(custom_electrode_selection)

        # Build electrode selection

        self.all_electrodes_toggle = QButtonGroup()
        self.all_electrodes_toggle.addButton(all_electrodes_button)
        self.all_electrodes_toggle.addButton(custom_electrodes_button)
        self.all_electrodes_toggle.setId(all_electrodes_button, 1)
        self.all_electrodes_toggle.setId(custom_electrodes_button, 2)
        self.all_electrodes_toggle.idPressed.connect(self.toggle_all_electrodes)

        electrode_selection = QVBoxLayout()
        electrode_selection.addWidget(all_electrodes_button)
        electrode_selection.addLayout(custom_electrodes_option)

        # Input Section Layout #

        # Titles
        data_recording_title = QLabel("Record Data")
        data_recording_title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        data_recording_title.setStyleSheet("""color: #fff;font-size: 15px;""")
        data_processing_title = QLabel("Data Processing Options")
        data_processing_title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        data_processing_title.setStyleSheet("""color: #fff;font-size: 15px;""")

        # # Groups
        #
        # # Record Data Group
        # state_recording_layout = QVBoxLayout()
        # state_recording_layout.addLayout(state_a)
        # state_recording_layout.addLayout(state_b)
        # state_recording_group = QGroupBox("Record Data")
        # state_recording_group.setLayout(state_recording_layout)
        # state_recording_group.setStyleSheet("""
        #     border-image: none !important;
        #     border-style: outset;
        #     border-width: 2px;
        #     border-radius: 10px;
        #     border-color: beige;
        #     color: #fff;
        #     font-size: 15px;
        # """)
        #
        # # Data Processing Options Group
        # data_processing_options_layout = QVBoxLayout()
        # data_processing_options_layout.addLayout(bandpower_selection)
        # data_processing_options_layout.addWidget(relative_plot_checkbox)
        # data_processing_options_layout.addWidget(sixty_hz_filter_checkbox)
        # data_processing_options_layout.addWidget(zero_to_five_hz_filter_checkbox)
        # data_processing_options_layout.addLayout(frequency_range_selection)
        # data_processing_options_layout.addLayout(electrode_selection)
        # data_processing_options_group = QGroupBox("Data Processing Options")
        # data_processing_options_group.setStyleSheet("""
        #     border-image: none !important;
        #     border-style: outset;
        #     border-width: 2px;
        #     border-radius: 10px;
        #     border-color: beige;
        #     color: #fff;
        #     font-size: 15px;
        # """)
        # data_processing_options_group.setLayout(data_processing_options_layout)

        input_layout = QGridLayout()
        input_layout.addWidget(data_recording_title, 0, 0)
        input_layout.addLayout(state_a, 1, 0)
        input_layout.addLayout(state_b, 2, 0)
        input_layout.addWidget(data_processing_title, 3, 0)
        input_layout.addLayout(bandpower_selection, 4, 0)
        input_layout.addWidget(relative_plot_checkbox, 5, 0)
        input_layout.addWidget(sixty_hz_filter_checkbox, 6, 0)
        input_layout.addWidget(zero_to_five_hz_filter_checkbox, 7, 0)
        input_layout.addLayout(frequency_range_selection, 8, 0)
        input_layout.addLayout(electrode_selection, 9, 0)

        # ############## #
        # Output Section #
        # ############## #

        # State A/B Graph #

        self.graph = Graph(self, self.parent)

        # Rescale graph button #

        rescale_graph_button = QPushButton("Rescale Graph")
        rescale_graph_button.pressed.connect(self.rescale_graph)
        rescale_graph_button.setStyleSheet("""
            border-image: none !important;
            border-style: outset;
            border-width: 2px;
            border-radius: 10px;
            border-color: beige;
            color: #fff;
            font-size: 15px;
        """)

        graph_w = QVBoxLayout()
        graph_w.addWidget(self.graph)
        graph_w.addWidget(rescale_graph_button)

        # State A Information #

        self.a_title_w = QLabel("State A")
        self.a_title_w.setStyleSheet("""color: #fff;font-size: 15px;""")

        self.a_frequency_spacing_w = QLabel("Frequency Bin Spacing (Hz): N/A")
        self.a_frequency_spacing_w.setStyleSheet("""color: #fff;font-size: 15px;""")

        self.a_delta_w = QLabel("Delta Relative Power: N/A")
        self.a_delta_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.a_theta_w = QLabel("Theta Relative Power: N/A")
        self.a_theta_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.a_alpha_w = QLabel("Alpha Relative Power: N/A")
        self.a_alpha_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.a_beta_w = QLabel("Beta Relative Power: N/A")
        self.a_beta_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.a_gamma_w = QLabel("Gamma Relative Power: N/A")
        self.a_gamma_w.setStyleSheet("""color: #fff;font-size: 15px;""")

        a_output_information = QVBoxLayout()
        a_output_information.addWidget(self.a_title_w)
        a_output_information.addWidget(self.a_frequency_spacing_w)
        a_output_information.addWidget(self.a_delta_w)
        a_output_information.addWidget(self.a_theta_w)
        a_output_information.addWidget(self.a_alpha_w)
        a_output_information.addWidget(self.a_beta_w)
        a_output_information.addWidget(self.a_gamma_w)

        # State B Information #

        self.b_title_w = QLabel("State B")
        self.b_title_w.setStyleSheet("""color: #fff;font-size: 15px;""")

        self.b_frequency_spacing_w = QLabel("Frequency Bin Spacing (Hz): N/A")
        self.b_frequency_spacing_w.setStyleSheet("""color: #fff;font-size: 15px;""")

        self.b_delta_w = QLabel("Delta Relative Power: N/A")
        self.b_delta_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.b_theta_w = QLabel("Theta Relative Power: N/A")
        self.b_theta_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.b_alpha_w = QLabel("Alpha Relative Power: N/A")
        self.b_alpha_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.b_beta_w = QLabel("Beta Relative Power: N/A")
        self.b_beta_w.setStyleSheet("""color: #fff;font-size: 15px;""")
        self.b_gamma_w = QLabel("Gamma Relative Power: N/A")
        self.b_gamma_w.setStyleSheet("""color: #fff;font-size: 15px;""")

        b_output_information = QVBoxLayout()
        b_output_information.addWidget(self.b_title_w)
        b_output_information.addWidget(self.b_frequency_spacing_w)
        b_output_information.addWidget(self.b_delta_w)
        b_output_information.addWidget(self.b_theta_w)
        b_output_information.addWidget(self.b_alpha_w)
        b_output_information.addWidget(self.b_beta_w)
        b_output_information.addWidget(self.b_gamma_w)

        # Output Section Layout #

        output_information = QGridLayout()
        output_information.addLayout(a_output_information, 0, 0)
        output_information.addLayout(b_output_information, 1, 0)

        output_layout = QGridLayout()
        output_layout.addLayout(graph_w, 0, 0)
        output_layout.addLayout(output_information, 0, 1)

        output_layout.setColumnStretch(0, 3)
        output_layout.setColumnStretch(1, 1)

        # ############ #
        # Macro Layout #
        # ############ #

        title = QLabel("Record and Compare Bandpowers in Two States")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet("""color: #fff; font-size: 15px;""")

        # Layout

        layout = QGridLayout()
        layout.addLayout(input_layout, 0, 0)
        layout.addLayout(output_layout, 0, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)

        self.setLayout(layout)

    def pressed_record_a(self):
        self.a_record_button.setText("Recording...")

    def record_a(self):
        num_data_points = self.parent.sampling_rate * self.a_record_time
        print('recording state a')
        time.sleep(self.a_record_time)  # let buffer get filled
        self.a_record_button.setText("Record State A")
        self.a_data = self.parent.board_shim.get_current_board_data(num_samples=num_data_points)[1:9]
        if self.a_data is not None and self.b_data is not None:
            self.process_bp()
        pd.DataFrame(np.transpose(self.a_data)).to_csv('state_raw_data/a_data.csv')

    def record_b_pressed(self):
        self.b_record_button.setText("Recording...")

    def record_b(self):
        num_data_points = self.parent.sampling_rate * self.b_record_time
        print('recording state b')
        time.sleep(self.b_record_time)  # let buffer get filled
        self.b_record_button.setText("Record State B")
        self.b_data = self.parent.board_shim.get_current_board_data(num_samples=num_data_points)[1:9]
        if self.a_data is not None and self.b_data is not None:
            self.process_bp()
        pd.DataFrame(np.transpose(self.b_data)).to_csv('state_raw_data/b_data.csv')

    def set_a_record_time(self, seconds):
        self.a_record_time = int(seconds)
        print(self.a_record_time)

    def set_b_record_time(self, seconds):
        self.b_record_time = int(seconds)
        print(self.b_record_time)

    def set_bp_method(self, i):
        self.selected_bp_method = self.bp_methods[i]
        print(self.selected_bp_method)
        self.process_bp()

    def set_relative_plot(self, i):
        if i == 0:
            self.relative_plot = False
        else:
            self.relative_plot = True
        print(self.relative_plot)
        self.process_bp()
        self.rescale_graph()

    def set_sixty_hz_filter(self, i):
        if i == 0:
            self.filter_sixty_hz = False
        else:
            self.filter_sixty_hz = True
        print(self.filter_sixty_hz)
        self.process_bp()

    def set_zero_to_five_hz_filter(self, i):
        if i == 0:
            self.filter_zero_to_five_hz = False
        else:
            self.filter_zero_to_five_hz = True
        print(self.filter_zero_to_five_hz)
        self.process_bp()

    def toggle_custom_frequency(self, i):
        if int(i) == 1:
            self.include_all_frequencies = True
        else:
            self.include_all_frequencies = False
        print(self.include_all_frequencies)
        self.process_bp()
        self.rescale_graph()

    def set_low_frequency(self, low):
        if low == "":
            self.custom_low_frequency = 0
        else:
            self.custom_low_frequency = int(low)
        print(self.custom_low_frequency)
        self.process_bp()
        if not self.include_all_frequencies:
            self.rescale_graph()

    def set_high_frequency(self, high):
        if high == "":
            self.custom_high_frequency = 125
        else:
            self.custom_high_frequency = int(high)
        print(self.custom_high_frequency)
        self.process_bp()
        if not self.include_all_frequencies:
            self.rescale_graph()

    def toggle_all_electrodes(self, i):
        if i == 1:
            self.include_all_electrodes = True
        else:
            self.include_all_electrodes = False
        print(self.include_all_electrodes)
        self.process_bp()

    def select_custom_electrode(self, electrode_num):
        if electrode_num in self.custom_electrode_selection:
            self.custom_electrode_selection.remove(electrode_num)
        else:
            self.custom_electrode_selection.append(electrode_num)
            self.custom_electrode_selection.sort()
        print(self.custom_electrode_selection)
        self.process_bp()

    def rescale_graph(self):
        self.graph.p.autoRange()

    # Processes the bandpower for states a and b given the current settings
    def process_bp(self):

        a_processed_channel_holder = []
        b_processed_channel_holder = []
        a_frequencies = []
        b_frequencies = []
        uncut_a_frequencies = []
        uncut_b_frequencies = []
        uncut_a_bandpowers = []
        uncut_b_bandpowers = []

        for i in range(0, NUM_ELECTRODES):
            if self.include_all_electrodes or (i+1) in self.custom_electrode_selection:
                a_channel = self.a_data[i] - np.mean(self.a_data[i])
                b_channel = self.b_data[i] - np.mean(self.b_data[i])

                if self.filter_sixty_hz:
                    DataFilter.perform_bandstop(a_channel, self.parent.sampling_rate, 60, 4,
                                                2, FilterTypes.BUTTERWORTH.value, 0.0)
                    DataFilter.perform_bandstop(b_channel, self.parent.sampling_rate, 60, 4,
                                                2, FilterTypes.BUTTERWORTH.value, 0.0)

                if self.filter_zero_to_five_hz:
                    band_pass_min = 5
                    band_pass_max = 125
                    center_freq = (band_pass_min + band_pass_max) / 2.0
                    band_width = band_pass_max - band_pass_min
                    DataFilter.perform_bandpass(a_channel, self.parent.sampling_rate, center_freq, band_width, 2,
                                                FilterTypes.BUTTERWORTH.value, 0.0)
                    DataFilter.perform_bandpass(b_channel, self.parent.sampling_rate, center_freq, band_width, 2,
                                                FilterTypes.BUTTERWORTH.value, 0.0)

                if self.selected_bp_method == "Welch's":
                    a_welch_window_length = int(self.welch_window_length_fraction_of_total * len(a_channel))
                    b_welch_window_length = int(self.welch_window_length_fraction_of_total * len(b_channel))
                    a_frequencies, a_power_spectral_density = \
                        signal.welch(a_channel, fs=self.parent.sampling_rate, nperseg=a_welch_window_length)
                    b_frequencies, b_power_spectral_density = \
                        signal.welch(b_channel, fs=self.parent.sampling_rate, nperseg=b_welch_window_length)
                elif self.selected_bp_method == "Multitaper":
                    a_power_spectral_density, a_frequencies = \
                        psd_array_multitaper(a_channel, self.parent.sampling_rate,
                                             adaptive=True, normalization='full', verbose=0)
                    b_power_spectral_density, b_frequencies = \
                        psd_array_multitaper(b_channel, self.parent.sampling_rate,
                                             adaptive=True, normalization='full', verbose=0)
                elif self.selected_bp_method == "FFT":
                    a_fft = np.fft.rfft(a_channel)
                    a_power_spectral_density = np.multiply(a_fft, np.conjugate(a_fft)).real
                    a_frequencies = np.fft.rfftfreq(len(a_channel), 1/self.parent.sampling_rate)
                    b_fft = np.fft.rfft(b_channel)
                    b_power_spectral_density = np.multiply(b_fft, np.conjugate(b_fft)).real
                    b_frequencies = np.fft.rfftfreq(len(b_channel), 1/self.parent.sampling_rate)
                else:
                    print('ERROR: Bandpower method is not implemented')
                    return

                uncut_a_frequencies = a_frequencies.copy()
                uncut_b_frequencies = b_frequencies.copy()
                uncut_a_bandpowers = a_power_spectral_density.copy()
                uncut_b_bandpowers = b_power_spectral_density.copy()

                if self.include_all_frequencies:
                    self.a_total_power = integrate.simps(a_power_spectral_density)
                    self.b_total_power = integrate.simps(b_power_spectral_density)
                else:
                    a_band_idx = np.logical_and(a_frequencies >= self.custom_low_frequency,
                                                a_frequencies <= self.custom_high_frequency)
                    a_frequencies = a_frequencies[a_band_idx]
                    a_power_spectral_density = a_power_spectral_density[a_band_idx]
                    self.a_total_power = integrate.simps(a_power_spectral_density)

                    b_band_idx = np.logical_and(b_frequencies >= self.custom_low_frequency,
                                                b_frequencies <= self.custom_high_frequency)
                    b_frequencies = b_frequencies[b_band_idx]
                    b_power_spectral_density = b_power_spectral_density[b_band_idx]
                    self.b_total_power = integrate.simps(b_power_spectral_density)

                # Get relevant band powers
                a_band_powers = []
                for j in range(len(a_frequencies)):
                    bin = a_frequencies[j]
                    band_power = a_power_spectral_density[j]
                    if self.relative_plot:
                        band_power = band_power / self.a_total_power
                    a_band_powers.append(band_power)

                b_band_powers = []
                for j in range(len(b_frequencies)):
                    bin = b_frequencies[j]
                    band_power = b_power_spectral_density[j]
                    if self.relative_plot:
                        band_power = band_power / self.b_total_power
                    b_band_powers.append(band_power)

                a_processed_channel_holder.append(a_band_powers)
                b_processed_channel_holder.append(b_band_powers)

        self.a_frequencies = np.array(a_frequencies)
        self.b_frequencies = np.array(b_frequencies)
        self.a_processed_bp = np.mean(a_processed_channel_holder, axis=0)
        self.b_processed_bp = np.mean(b_processed_channel_holder, axis=0)

        self.graph.clear_plots()

        # Plot A
        self.graph.plot_a(self.a_frequencies, self.a_processed_bp)

        # Plot B
        self.graph.plot_b(self.b_frequencies, self.b_processed_bp)

        # Get Band Powers #

        for i in range(len(uncut_a_frequencies)):
            if uncut_a_frequencies[i] not in a_frequencies:
                uncut_a_frequencies[i] = 0
                uncut_a_bandpowers[i] = 0

        for i in range(len(uncut_b_frequencies)):
            if uncut_b_frequencies[i] not in b_frequencies:
                uncut_b_frequencies[i] = 0
                uncut_b_bandpowers[i] = 0

        for i in range(len(EEG_BANDS)):
            start_freq = EEG_BANDS[i][0]
            end_freq = EEG_BANDS[i][1]

            # Process bands for a
            uncut_a_band_idx = np.logical_and(uncut_a_frequencies >= start_freq,
                                              uncut_a_frequencies <= end_freq)
            a_band_psd = uncut_a_bandpowers[uncut_a_band_idx]
            if len(a_band_psd) > 1:
                a_band_power = integrate.simps(a_band_psd)
            else:
                a_band_power = 0
            self.a_standard_band_values[i] = a_band_power / self.a_total_power

            # Process bands for b
            uncut_b_band_idx = np.logical_and(uncut_b_frequencies >= start_freq,
                                              uncut_b_frequencies <= end_freq)
            b_band_psd = uncut_b_bandpowers[uncut_b_band_idx]
            if len(b_band_psd) > 1:
                b_band_power = integrate.simps(b_band_psd)
            else:
                b_band_power = 0
            self.b_standard_band_values[i] = b_band_power / self.b_total_power

        self.update_output_information()

    def update_output_information(self):
        self.a_title_w.setText("State A (Recorded " + str(self.a_record_time) + " seconds of data)")
        self.a_frequency_spacing_w.setText("Frequency Bin Spacing (Hz): "
                                           + str(round(self.a_frequencies[1] - self.a_frequencies[0], 3)))
        self.a_delta_w.setText("Delta Relative Power: " + str(round(self.a_standard_band_values[0], 3)))
        self.a_theta_w.setText("Theta Relative Power: " + str(round(self.a_standard_band_values[1], 3)))
        self.a_alpha_w.setText("Alpha Relative Power: " + str(round(self.a_standard_band_values[2], 3)))
        self.a_beta_w.setText("Beta Relative Power: " + str(round(self.a_standard_band_values[3], 3)))
        self.a_gamma_w.setText("Gamma Relative Power: " + str(round(self.a_standard_band_values[4], 3)))

        self.b_title_w.setText("State B (Recorded " + str(self.b_record_time) + " seconds of data)")
        self.b_frequency_spacing_w.setText("Frequency Bin Spacing (Hz): "
                                           + str(round(self.b_frequencies[1] - self.b_frequencies[0], 3)))

        self.b_delta_w.setText("Delta Relative Power: " + str(round(self.b_standard_band_values[0], 3)))
        self.b_theta_w.setText("Theta Relative Power: " + str(round(self.b_standard_band_values[1], 3)))
        self.b_alpha_w.setText("Alpha Relative Power: " + str(round(self.b_standard_band_values[2], 3)))
        self.b_beta_w.setText("Beta Relative Power: " + str(round(self.b_standard_band_values[3], 3)))
        self.b_gamma_w.setText("Gamma Relative Power: " + str(round(self.b_standard_band_values[4], 3)))


class Graph(pg.GraphicsLayoutWidget):

    def __init__(self, plotSelf, parentSelf):
        self.plotSelf = plotSelf
        self.parentSelf = parentSelf
        super().__init__()
        self.p = self.addPlot(row=0, col=0)
        self.legend = self.p.addLegend()

    def plot_a(self, x, y):
        plot_item = self.p.plot(x, y, pen=pg.mkPen(color=(0, 138, 0)))
        self.legend.addItem(plot_item, "State A")

    def plot_b(self, x, y):
        plot_item = self.p.plot(x, y, pen=pg.mkPen(color=(200, 138, 0)))
        self.legend.addItem(plot_item, "State B")

    def clear_plots(self):
        self.p.clear()
