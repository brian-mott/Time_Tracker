"""
A timer app used to track productive time towards a daily goal
One timer counts down towards the daily goal and a stopwatch counts up for amount of time spent on a given task

The user can change the daily countdown goal, edit categories of activities, and see graphed 
results over time regarding time spent per day and weekly averages

Logic

    The timers track total seconds; these are converted to hh:mm:ss for easy interpretation
    Each start and pause generates a timestamp. This timestamp and the selected activity are saved to a sqlite3 database
    Database schema:
        log table that records timestamps and activities
        categories table to normalize activities and their category grouping
    Time data can then be aggregated and summed in various ways for analysis and graphing
        Dataframes are used for aggregating
        Graphing done with matplotlib 
    
main_app for frames and windows
datetimefuncs with classes that handle conversion from seconds to hh:mm:ss; calculating last 7 or 30 days for df filtering
dbsanddfs with classes for SQLalchemy db setup and manipulaiton of df for graphing and logging

UI layout:
    4 main tabs:
        Timer
        Graphs/Analysis
        Log
        Setup
    Each tab is its own frame
    Graph/Analysis frame contains placeholder frame at location where graph objects are displayed
    Frames are packed into tabs
    Grids for finer frame layout

Graphing handled within the Analysis frame class
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from tkinter.messagebox import showinfo, showwarning
from datetime import datetime
from dbsanddfs import SQLAlchemyDB, AnalysisGraphDFs
from datetimefuncs import TimerFuncs
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)

# allow other classes to create instances
app = None

# matplotlib set backend, this needs to be in place along with the canvas.draw_idle() to not get seg fault
matplotlib.use('TkAgg')

# set appearance and theme
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('green')

# database instance, change this to ensure all frames and classes access same file
DB = SQLAlchemyDB('data.db')



class TimerFrame(ctk.CTkFrame):
    """
    Frame for countdown timer and stopwatch
    Timer logic included

    TimerFuncs class from datetimefuncs contains helper functions for formatting
    of seconds into hours, min, sec
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # frame column and row configure
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # timer variables
        self.running = False
        self.seconds_cd = TimerFuncs.get_total_seconds(8, 0, 0)
        # start seconds to compute proportion of task bar
        self.start_seconds_cd = self.seconds_cd
        self.seconds_sw = 0
        self.update_time = ''

        # initial null timestamps
        self.timestamp_start = None
        self.timestamp_end = None

        # categories variables
        # dict for foreign key of log table
        # list for options widget
        self.categories = DB.view_categories()
        self.category_dict = {item[1]: item[0] for item in self.categories}
        self.option_menu_list = [i for i in self.category_dict.keys()]

        self.create_widgets()


    def create_widgets(self):
        # Top with timers and progress bar
        label_fonts = {'font': ('Arial', 20)}
        timer_fonts = {'font': ('Monaco', 80)}

        # countdown
        self.header = ctk.CTkLabel(self, text='Daily Countdown', **label_fonts)
        self.header.grid(row=0, column=0, columnspan=4, padx=10, pady=5)

        self.countdown_label=ctk.CTkLabel(self, corner_radius=8, text=TimerFuncs.formatted_time(self.seconds_cd), fg_color='#D84A2B', **timer_fonts)
        self.countdown_label.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

        # progress bar
        self.countdown_progress=ctk.CTkProgressBar(self, width=400, progress_color='#DCD31C')
        self.countdown_progress.set(0)
        self.countdown_progress.grid(row=2, column=0, columnspan=4, padx=5, pady=15)

        # count up
        self.stopwatch_label = ctk.CTkLabel(self, corner_radius=8, text=TimerFuncs.formatted_time(self.seconds_sw), fg_color='#66A75D', **timer_fonts)
        self.stopwatch_label.grid(row=3, column=0, columnspan=4, padx=5, pady=5)

        # activity label
        self.actvity_label = ctk.CTkLabel(self, text='For Activity:', **label_fonts)
        self.actvity_label.grid(row=4, column=0, columnspan=4, padx=30, pady=(10, 5))

        # activity options
        self.activity_options = ctk.CTkOptionMenu(self, values=self.option_menu_list, **label_fonts)
        self.activity_options.grid(row=5, column=0, columnspan=4, padx=30, pady=(10, 20))

        # Bottom half with buttons
        button_options = {
            'height': 60,
            'width': 95,
            'font': ('Arial', 20),
        }

        button_pady = {'pady': 3, 'padx': 3}

        self.start_button = ctk.CTkButton(self, text='Start', command=self.start, **button_options)
        self.start_button.grid(row=6, column=0, **button_pady)

        self.pause_button = ctk.CTkButton(self, text="Pause", command=self.pause, **button_options)
        self.pause_button.grid(row=6, column=1, **button_pady)

        self.resetsw_button = ctk.CTkButton(self, text='Reset\nTop', command=self.reset_countdown, **button_options)
        self.resetsw_button.grid(row=6, column=2, **button_pady)

        self.resetcd_button = ctk.CTkButton(self, text='Reset\nBottom', command=self.reset_stopwatch, **button_options)
        self.resetcd_button.grid(row=6, column=3, **button_pady)


    # timer methods
    def start(self, event=None):
        # disable reset buttons
        self.resetcd_button.configure(state='disabled')
        self.resetsw_button.configure(state='disabled')
        # disable set timer button on setup frame
        app.tab_view.setup_frame.set_timer_button.configure(state='disabled')

        if not self.running:
            self.update()
            self.running = True
        # prevent resetting start timestamp if pressing start after timer running
        if not self.timestamp_start:
            self.timestamp_start = datetime.now()
    

    def update(self):
        # change counts down and up
        self.seconds_cd -= 1
        self.seconds_sw += 1

        # update labels
        self.countdown_label.configure(text=TimerFuncs.formatted_time(self.seconds_cd))
        self.stopwatch_label.configure(text=TimerFuncs.formatted_time(self.seconds_sw))

        # update progress bar
        self.progress_calc = (self.start_seconds_cd - self.seconds_cd) / self.start_seconds_cd
        self.countdown_progress.set(self.progress_calc)

        # schedule another timer
        self.update_time = self.stopwatch_label.after(1000, self.update)

        # when countdown runs out
        if self.seconds_cd == 0:
            self.pause()
            showinfo(message=f'You reached your goal of {TimerFuncs.formatted_time(self.start_seconds_cd)} of productive time!')


    def pause(self):
        # enable reset buttons
        self.resetcd_button.configure(state='normal')
        self.resetsw_button.configure(state='normal')
        # enable timer set button on setup tab/frame
        app.tab_view.setup_frame.set_timer_button.configure(state='normal')

        if self.running:
            # after cancel needed to pause, not sure why
            self.stopwatch_label.after_cancel(self.update_time)
            self.running = False
        
        self.timestamp_end = datetime.now()

        # prevent adding incomplete logs or multiple entries by spamming pause button
        if self.timestamp_start and self.timestamp_end:
            activity_int = self.category_dict[self.activity_options.get()]
            DB.insert_timestamp(activity_int, self.timestamp_start, self.timestamp_end)
        
        # reset timestamps
        self.timestamp_start = None
        self.timestamp_end = None


    def reset_stopwatch(self):
        if self.running:
            self.stopwatch_label.after_cancel(self.update_time)
            self.running = False
        self.seconds_sw = 0
        self.stopwatch_label.configure(text=TimerFuncs.formatted_time(self.seconds_sw))


    def reset_countdown(self):
        if self.running:
            self.countdown_label.after_cancel(self.update_time)
            self.running = False
        # reset to previous start second variable to keep consistent with setup tab
        self.seconds_cd = self.start_seconds_cd
        # start seconds for reference to compute proportion of completed progress bar
        self.progress_calc = 0
        self.countdown_progress.set(self.progress_calc)
        self.countdown_label.configure(text=TimerFuncs.formatted_time(self.seconds_cd))



class AnalysisFrame(ctk.CTkFrame):
    """
    Frame that handles graphing of log data
    Bargraph that can change based on time range
    Boxplot based on day of week for summary statistics

    With splitting out the assignment and placing of widget and figure, can now destroy graph after use        
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # configured to use same db info as set for the whole app
        self.analysis_instance = AnalysisGraphDFs(db_instance=DB)
        
        # set dark style for plots
        plt.style.use('dark_background')

        # frame grid
        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=10)    # row with graph object
        self.grid_rowconfigure((3, 4), weight=1)

        self.columnconfigure((0, 1, 2), weight=1)
        
        # variables
        self.seg_button_var = ctk.StringVar(value='Bar Graph')
        self.radio_var = ctk.IntVar(value=7)
        self.plot_df = self.analysis_instance.get_df_summary(days=self.radio_var.get())
        
        # needed for closing out plot objects before drawing new one
        self.fig = None
        self.graph_widget = None
        self.toolbar = None

        # intially place widgets
        self.create_widgets()


    def create_widgets(self):
        # widgets
        # header
        self.header = ctk.CTkLabel(self, text='Graphs and Charts', font=('Arial', 20))
        self.header.grid(row=0, column=1, sticky='nsew')

        # segment button for graph type
        self.segment_button = ctk.CTkSegmentedButton(self, values=['Bar Graph', 'Boxplot'], variable=self.seg_button_var, command=self.seg_button_callback)
        self.segment_button.grid(row=1, column=0, columnspan=3, sticky='ew')

        # graph placed in its own frame to prevent weird full window jitter when destroying and creating new graph objects
        self.frame = ctk.CTkFrame(self, width=408, height=340)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.frame.grid(row=2, column=0, columnspan=3, padx=0, pady=0, ipadx=0, ipady=0, sticky='nsew')
        self.create_graph()

        # radio buttons
        self.radiobutton1 = ctk.CTkRadioButton(self, text='Past 7 Days', variable=self.radio_var, value=7, command=self.get_radio_button)
        self.radiobutton1.grid(row=4, column=0, ipadx=5, ipady=2)
        self.radiobutton2 = ctk.CTkRadioButton(self, text='Past 30 Days', variable=self.radio_var, value=30, command=self.get_radio_button)
        self.radiobutton2.grid(row=4, column=1, ipadx=5, ipady=2)
        self.radiobutton3 = ctk.CTkRadioButton(self, text='All Days', variable=self.radio_var, value=365, command=self.get_radio_button)
        self.radiobutton3.grid(row=4, column=2, ipadx=5, ipady=2)


    def get_radio_button(self):
        """creates new graph based on selected radio button"""
        self.create_graph(self.seg_button_var.get())
    

    # grabs summary df filtered on number of days needed and creates figure objects
    def create_graph(self, seg_button_value='Bar Graph'):
        """
        creates graphing objects and place them in frame
        parameter to return bar graph or boxplot

        if plot, canvas, and toolbar already exist, destroys them before creating new objects
        """
        # filter df based on date range selected
        if seg_button_value == 'Bar Graph':
            plot_df = self.analysis_instance.get_df_summary(days=self.radio_var.get())
        
        if seg_button_value == 'Boxplot':
            plot_df = self.analysis_instance.get_df_summary(days=365)

        # destroy prior objects before creating new ones, different scales for graphs so makes more sense
        # to create and destroy instead of modify
        if self.fig:
            plt.close()
        
        if self.graph_widget:
            self.graph_widget.destroy()
        
        if self.toolbar:
            self.toolbar.destroy()
        
        # configuration of axes and parameters
        self.fig, self.axes = plt.subplots()

        # set type of graph
        if seg_button_value == 'Bar Graph':
            self.axes.bar(plot_df['date'], plot_df['duration'])

        # seaborn boxplot created directly off of df instead of needing arrays like standard matplotlib boxplot function
        if seg_button_value == 'Boxplot':
            sns.boxplot(data=plot_df, x='DayOfWeek', y='duration')

        self.fig.set_dpi(100)
        self.fig.set_size_inches(1.9, 2.9)
        self.axes.set_facecolor('#333333')
        self.fig.patch.set_facecolor('#333333')
        self.axes.set_ylabel('Hours')
        self.fig.subplots_adjust(top=0.98, bottom=0.23, wspace=0, hspace=0)

        # rotate tick marks, gives constant warning: FixedFormatter should only be used together with FixedLocator
        # warning now gone after first calling set_xticks() method
        self.axes.set_xticks(self.axes.get_xticks())
        self.axes.set_xticklabels(self.axes.get_xticklabels(), rotation=45)

        # create canvas objects
        # draw_idle and flush_events methods might be needed to prevent seg fault with redrawing plots after clearing old plots
        # place objects in placeholder frrame
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.canvas.draw_idle()
        self.canvas.flush_events()

        self.graph_widget = self.canvas.get_tk_widget()
        # placed in place holder frame
        self.graph_widget.grid(sticky='nsew', row=0, column=0, padx=0, pady=0, ipadx=0, ipady=0)

        # with pack_toolbar=False, can then use on a grid system
        self.toolbar = NavigationToolbar2Tk(self.canvas, pack_toolbar=False)
        self.toolbar.grid(row=3, column=0, columnspan=3, sticky='ew')
        

    def seg_button_callback(self, value):
        """
        Callback for seg button
        Calls method for updating the graph
        Enables or disables radio buttons for bargraph time range
        """
        radiobuttons = (self.radiobutton1, self.radiobutton2, self.radiobutton3)

        value = self.seg_button_var.get()
        self.create_graph(value)

        if value == 'Bar Graph':
            for button in radiobuttons:
                button.configure(state='normal')
        else:
            for button in radiobuttons:
                button.configure(state='disabled')
    


class LogFrame(ctk.CTkFrame):
    """
    Frame and tab for looking at all log files

    Method to create tree after selection of segmented button
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # grid configure
        self.grid_rowconfigure((0, 1), weight=0)
        self.grid_rowconfigure(2, weight=3)     # treeview row

        # seg button variable
        self.seg_button_var = ctk.StringVar(value='Days')

        self.log_df = AnalysisGraphDFs(db_instance=DB)

        self.df_method_dict = {
            'Days': self.log_df.get_df_log_summary(),
            'Weeks': self.log_df.get_df_log_summary_weeks(),
            'Months': self.log_df.get_df_log_summary_months()
        }

        self.create_widgets()
    

    def create_widgets(self):
        """Default to create daily view"""
        # header
        self.header = ctk.CTkLabel(self, text='Aggregated Durations', font=('Arial', 20))
        self.header.grid(row=0, pady=5, sticky='ew')

        # segmented button
        self.segment_button = ctk.CTkSegmentedButton(self, values=['Days', 'Weeks', 'Months'], variable=self.seg_button_var, command=self.seg_button_callback)
        self.segment_button.grid(row=1, pady=5, sticky='ew')

        # initial tree creation with hardcoding for days
        self.create_tree('Days')


    def create_tree(self, seg_button_value):
        """
        Method to create tree based off of segmented button value, either 'Days' 'Weeks' or 'Months'
        column_header_dict = header names match df names, argument passed to bound command to sort or reverse sort
        """
        column_key = seg_button_value

        column_header_dict = {
            'Days': {
                'header': ['date', 'DayOfWeek', 'hms_duration'],
                'text': ['Date', 'Day', 'Total Time'],
            },
            'Weeks': {
                'header': ['week_start', 'day', 'hms_duration'],
                'text': ['Week of', 'Start of Week', 'Total Time'],
            },
            'Months': {
                'header': ['year_month', 'month_name', 'hms_duration'],
                'text': ['Year and Month', 'Month', 'Total Time']
            }
        }

        headers = [item for item in column_header_dict[column_key]['header']]
        texts = [item for item in column_header_dict[column_key]['text']]

        self.tree = ttk.Treeview(self, columns=headers, show='headings')

        for header, text in zip(headers, texts):
            # extra lambda col=header insures header is correctly assigned for each iteration
            self.tree.heading(f'{header}', text=text, command=lambda col=header: self.sort_column(column=col))
            self.tree.column(header, width=136)
        
        self.tree.grid(row=2, sticky='nsew')

        self.update_tree()
        

    def seg_button_callback(self, seg_button_value):
        """Creates new tree based on seg button value"""
        seg_button_value = self.seg_button_var.get()
        self.create_tree(seg_button_value)


    def update_tree(self, df=None):
        """
        Updates tree with the appropriate log summary df for Days, Weeks, or Months
        Uses df_method_dict in __init__ to call proper method to return the df
        """
        seg_button = self.seg_button_var.get()

        # clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # get correct method to return correct df
        if df is None:
            df = self.df_method_dict.get(seg_button)

        # insert into tree
        counter = len(df)
        for i in range(counter):
            self.tree.insert('', i, values=df.iloc[i,:].tolist())
    

    def sort_column(self, column, ascending=False):
        """
        Sorts column on click of heading
        Based on getting Days Weeks or Months df and then sorting df based on header name
        Header names match df column names

        Clicking again reverses sort order
        """
        # get seg button value to get proper df
        seg_button = self.seg_button_var.get()
        df = self.df_method_dict.get(seg_button)
        df = df.sort_values(by=[f'{column}'], inplace=True, ascending=ascending)

        # reset column heading command to do opposite of last sort action
        self.tree.heading(f'{column}', command=lambda: self.sort_column(column=column, ascending=not ascending))
        
        # update based on just created and sorted df instead of default values for update_tree method
        self.update_tree(df=df)



class EntryModifyWindow(ctk.CTkToplevel):
    """
    Class for creating popup window to add or edit activities and categories
    Parameters:
        win_title: title for window
        win_type: add or edit, determines method assignment and ok button callback
    
    Same layout for both edit and add windows, control flow to switch variable assignment and ok button callbacks 
    depending on the window title
    """
    def __init__(self, win_title, win_type='add', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.win_title = win_title
        self.win_type = win_type

        # set empty for add
        self.activity = ''
        self.category = ''

        # grab entry items for edit
        if self.win_type == 'edit':
            self.selected_item = app.tab_view.setup_frame.tree.selection()
            self.activity = app.tab_view.setup_frame.tree.item(self.selected_item)['values'][0]
            self.category = app.tab_view.setup_frame.tree.item(self.selected_item)['values'][1]
            self.ok_command_callback = self.ok_command_edit_callback
        

        self.activity_var = ctk.StringVar(app.tab_view.setup_frame, value=self.activity)
        self.category_var = ctk.StringVar(app.tab_view.setup_frame, value=self.category)

        # window layout
        self.geometry('250x180')
        self.title(f'{self.win_title}')

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.rowconfigure((0, 1, 2, 3), weight=0)
        self.rowconfigure(4, weight=1)

        padding = {
            'padx': 10,
            'pady': 2,
        }

        # activity label and entry
        self.activity_label = ctk.CTkLabel(self, text='Enter Activity:')
        self.activity_label.grid(row=0, column=0, columnspan=2, sticky='sw', **padding)

        self.activity_entry = ctk.CTkEntry(self, width=150, textvariable=self.activity_var)
        self.activity_entry.grid(row=1, column=0, columnspan=2, sticky='sew', **padding)
        self.activity_entry.focus()

        # category label and entry
        self.category_label= ctk.CTkLabel(self, text='Enter Category:')
        self.category_label.grid(row=2, column=0, columnspan=2, sticky='sw', **padding)

        self.category_entry = ctk.CTkEntry(self, width=150, textvariable=self.category_var)
        self.category_entry.grid(row=3, column=0, columnspan=2, stick='sew', **padding)

        # ok button, default set for add window
        self.ok_button = ctk.CTkButton(self, text='OK', width=100, command=self.ok_command_add_callback)
        self.ok_button.grid(row=4, column=0, sticky='w', **padding)
        self.bind('<Return>', self.ok_command_add_callback)

        if self.win_type == 'edit':
            self.ok_button.configure(command=self.ok_command_edit_callback)
            self.bind('<Return>', self.ok_command_edit_callback)

        # cancel button
        self.cancel_button = ctk.CTkButton(self, text='Cancel', width=100, command=self.cancel_command_callback)
        self.cancel_button.grid(row=4, column=1, sticky='e', **padding)


    def ok_command_edit_callback(self, event=None):

        # get current entry values
        new_activity=self.activity_var.get() 
        new_category=self.category_var.get()

        # check for blank or existing activities
        if new_activity == '':
            showwarning(message='Please enter an activity')
            # refocus on edit window and activity entry after warning box
            self.focus()
            self.activity_entry.focus()

        else: 
            DB.update_activity(old_activity=self.activity, old_category=self.category, new_activity=new_activity, new_category=new_category)
            self.destroy()
            app.tab_view.setup_frame.update_activity_entry()
    

    def ok_command_add_callback(self, event=None):
        new_activity=self.activity_var.get() 
        new_category=self.category_var.get()

        # check for blank or existing activities
        if new_activity == '':
            showwarning(message='Please enter an activity')
            self.focus()
            self.activity_entry.focus()

        elif new_activity in app.tab_view.timer_frame.option_menu_list:
            showwarning(message='Activity already exists!')
            self.focus()
            self.activity_entry.focus()

        else: 
            DB.insert_activity(activity=new_activity, category=new_category)
            self.destroy()
            app.tab_view.setup_frame.update_activity_entry()
    

    def cancel_command_callback(self):
        self.destroy()
        app.tab_view.setup_frame.update_activity_entry()



class SetupFrame(ctk.CTkFrame):
    """
    Frame and tab for setting countdown timer and editing activity categories
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # grid setup
        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.grid_rowconfigure(5, weight=8)     # treeview row
        self.grid_rowconfigure(6, weight=1)

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=2)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(4, weight=2)

        # entry variables, currently hard-coded for default
        self.hour_entry_var = ctk.StringVar(value='08')
        self.min_entry_var = ctk.StringVar(value='00')
        self.sec_entry_var = ctk.StringVar(value='00')

        self.toplevel_window = None

        self.create_widgets()


    def create_widgets(self):
        no_padding = {
            'padx': 0,
            'pady': 0,
            'ipadx': 0,
            'ipady': 0
        }

        padding = {
            'padx': 2,
            'pady': 2,
        }

        # header
        self.header = ctk.CTkLabel(self, text='Set Countdown Timer', font=('Arial', 20))
        self.header.grid(row=0, column=0, columnspan=5, sticky='ew', **padding)

        # row with labels
        self.hour_label = ctk.CTkLabel(self, text='Hours')
        self.hour_label.grid(row=1, column=0, sticky='ew', **padding)

        self.min_label = ctk.CTkLabel(self, text='Minutes')
        self.min_label.grid(row=1, column=2, sticky='ew', **padding)

        self.sec_label = ctk.CTkLabel(self, text='Seconds')
        self.sec_label.grid(row=1, column=4, sticky='ew', **padding)

        # row with entries
        self.hour_entry = ctk.CTkEntry(self, textvariable=self.hour_entry_var)
        self.hour_entry.grid(row=2, column=0, sticky='ew', **padding)

        self.colon_label1 = ctk.CTkLabel(self, text=':')
        self.colon_label1.grid(row=2, column=1, sticky ='ew', **no_padding)

        self.min_entry = ctk.CTkEntry(self, textvariable=self.min_entry_var)
        self.min_entry.grid(row=2, column=2, sticky='ew', **padding)

        self.colon_label2 = ctk.CTkLabel(self, text=':')
        self.colon_label2.grid(row=2, column=3, sticky ='ew', **no_padding)

        self.sec_entry = ctk.CTkEntry(self, textvariable=self.sec_entry_var)
        self.sec_entry.grid(row=2, column=4, sticky='ew', **padding)

        # set button
        self.set_timer_button = ctk.CTkButton(
            self, 
            text='Set Timer', 
            width=20, 
            command=lambda: self.get_timer_input(
                hours=self.hour_entry_var.get(),
                mins=self.min_entry_var.get(),
                secs=self.sec_entry_var.get()
            )
        )
        self.set_timer_button.grid(row=3, column=2, sticky='ew', pady=(5, 0))

        # label for activity entry editing
        self.activity_label = ctk.CTkLabel(self, text='Edit Activities', font=('Arial', 20))
        self.activity_label.grid(row=4, column=0, columnspan=5, pady=5, sticky='ew')

        # treeview
        columns = ['activity', 'category']
        self.tree = ttk.Treeview(self, columns=columns, show='headings')

        # tree headings 
        self.tree.heading('activity', text='Activity')
        self.tree.heading('category', text='Category')

        # tree columns
        self.tree.column('activity', width=150)
        self.tree.column('category', width=150)
        # bind doubleclick to edit entry
        self.tree.bind("<Double-1>", self.edit_activity_entry)

        self.tree.grid(row=5, column=0, columnspan=5, sticky='nsew')

        # row for editing buttons
        self.add_button = ctk.CTkButton(self, text='+', width=30, command=self.add_activity_entry)
        self.add_button.grid(row=6, column=0, sticky='w')

        self.delete_button = ctk.CTkButton(self, text='-', width=30, command=self.delete_activity_entry)
        self.delete_button.grid(row=6, column=0, sticky='w', padx=35)

        self.edit_button = ctk.CTkButton(self, text='Edit', width=40, command=self.edit_activity_entry)
        self.edit_button.grid(row=6, column=2)

        self.update_button = ctk.CTkButton(self, text='Update', width=40, command=self.update_activity_entry)
        self.update_button.grid(row=6, column=4, sticky='e')
    
        self.update_activity_entry()    

    
    def get_timer_input(self, hours, mins, secs, event=None):
        """
        Method to validate input for countdown timer and return timer variables to timer frame
        """
        valid_num = False
        valid_time = False

        try:
            hours = int(hours)
            mins = int(mins)
            secs = int(secs)
            valid_num = True

        except ValueError as e:
            showinfo(title='Entry Error', message='Please enter a number!')
        
        # check for correct range
        if valid_num:
            if hours < 0 or hours > 24:
                showinfo(title='Hours error', message='Please enter hours between 0 and 24')

            elif mins < 0 or mins > 59:
                showinfo(title='Minutes error', message='Please enter minutes between 0 and 60')

            elif secs < 0 or secs > 59:
                showinfo(title='Seconds error', message='Please enter seconds between 0 and 60')

            elif hours == 0 and mins == 0 and secs == 0:
                showinfo(title='No time to countdown', message='Please enter time above 00:00:00')
            
            else:
                valid_time = True

        # if type and range correct, then update all appropriate variables 
        if valid_time:
            total_seconds = TimerFuncs.get_total_seconds(hours, mins, secs)
            app.tab_view.timer_frame.seconds_cd = total_seconds
        
            # current validation is to disable button to set new time while timer is running
            app.tab_view.timer_frame.countdown_label.configure(text=TimerFuncs.formatted_time(total_seconds))
            
            # update progress bar variables
            app.tab_view.timer_frame.start_seconds_cd = total_seconds
            app.tab_view.timer_frame.progress_calc = 0
            app.tab_view.timer_frame.countdown_progress.set(app.tab_view.timer_frame.progress_calc)

            valid_time = False


    def update_activity_entry(self):
        """
        Updates listbox with current category table
        Only displays the activity and grouping columns
        """
        # clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        # repopulate with up to date items
        for row in DB.view_categories():
            self.tree.insert('', tk.END, values=row[1:3])
        
        # update list and dict for selecting activity to track
        categories = DB.view_categories()
        category_dict = {item[1]: item[0] for item in categories}
        option_menu_list = [i for i in category_dict.keys()]

        # reset timer frame variables with the above
        if app:
            app.tab_view.timer_frame.category_dict = category_dict
            app.tab_view.timer_frame.option_menu_list = option_menu_list
            app.tab_view.timer_frame.activity_options.configure(values=option_menu_list)

            # check if item still exists and reset to start of list if selected item deleted since timer started
            selected_option = app.tab_view.timer_frame.activity_options.get()
            
            if selected_option not in option_menu_list:
                app.tab_view.timer_frame.activity_options.set(option_menu_list[0])


    def add_activity_entry(self):
        """
        Method for creating new window and subsequently adding new entry
        DB methods for adding a row to the db handled within methods for the EntryModifyWindow class
        """
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            self.toplevel_window = EntryModifyWindow(win_title='Add Activity', win_type='add')
        else:
            self.toplevel_window.focus()


    def delete_activity_entry(self):
        """Method to delete entry and then refresh tree"""
        selected_item = self.tree.selection()
        activity = self.tree.item(selected_item)['values'][0]
        category = self.tree.item(selected_item)['values'][1]
        DB.delete_activity(activity=activity, category=category)
        self.update_activity_entry()


    def edit_activity_entry(self, event=None):
        """
        Method for creating new window and subsequently editing selected entry
        DB methods for editing the row within the db handled within methods for the EntryModifyWindow class
        """
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            try:   
                self.toplevel_window = EntryModifyWindow(win_title='Edit Activity', win_type='edit')
            except IndexError:
                showwarning(message='Please select an activity to edit')
            
        else:
            self.toplevel_window.focus()
        


class TabView(ctk.CTkTabview):
    """
    Class to create tabs
    Easiest to use pack to fully fill window
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # add tabs
        self.add('Timer')
        self.add('Graphs')
        self.add('Log')
        self.add('Setup')

        # setup tab layouts
        self.timer_tab()
        self.analysis_tab()
        self.log_tab()
        self.setup_tab()


    def timer_tab(self):
        self.timer_frame = TimerFrame(self.tab('Timer'))
        self.timer_frame.pack(expand=True, fill='both', padx=0, pady=0)


    def analysis_tab(self):
        self.analysis_frame = AnalysisFrame(self.tab('Graphs'))
        self.analysis_frame.pack(expand=True, fill='both', padx=0, pady=0)


    def log_tab(self):
        self.log_frame = LogFrame(self.tab('Log'))
        self.log_frame.pack(expand=True, fill='both', padx=0, pady=0)


    def setup_tab(self):
        self.setup_frame = SetupFrame(self.tab('Setup'))
        self.setup_frame.pack(expand=True, fill='both', padx=0, pady=0)



class Application(ctk.CTk):
    """
    Main app class
    easiest to pack tabs to maximally fill window
    """
    def __init__(self, *args, **kwargs):
        super().__init__()

        # root window setup
        self.title('Daily Task Timers')
        self.geometry('420x525')
        self.resizable(0,0)

        self.tab_view = TabView(self)
        self.tab_view.pack(expand=True, fill='both')


# run the main loop
if __name__ == '__main__':
    app = Application()
    app.mainloop()