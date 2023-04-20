import tkinter as tk
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, select, join, text, insert, delete, update
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, DateTime
from datetime import date, datetime, timedelta
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)
from datetimefuncs import TimerFuncs, TimeDeltaDays



class SQLAlchemyDB:
    """
    Class for managing sqlite3 database of timestamps and categories
    Best to implement the methods but can also create an instance and use basic sqlalchemy methods off of this class
    
    parameters:
        db_path: set path to create new db or use previously created db
        engine_echo: True by default to see sqlalchemy info
    
    category table:
        id: primary key
        activity: string for activity
        grouping: category of activity
    
    log table:
        id: primary key
        taskid: foreign key constraint from category.id table
        start: datetime, starting timestamp of activity
        stop: datetime, ending timestamp of activity
        comments: text, for adding any comments through db manager apps if needed
    
    """
    def __init__(self, db_path, engine_echo=True):
        self.db_path = db_path
        self.engine_echo= engine_echo

        # sqlalchemy setup
        self.engine = create_engine(f'sqlite:///{db_path}', echo=self.engine_echo)
        self.meta = MetaData()

        # sqlalchemy tables
        self.category_table = Table(
            'category', self.meta,
            Column('id', Integer, primary_key=True),
            Column('activity', String, nullable=False),
            Column('grouping', String)
        )
        self.log_table = Table(
            'log', self.meta,
            Column('id', Integer, primary_key=True),
            Column('taskid', Integer, ForeignKey('category.id', ondelete='SET NULL'), nullable=False),
            Column('start', DateTime),
            Column('stop', DateTime),
            Column('comments', String)
        )

        # find or create tables
        self.meta.create_all(self.engine)

        # check if category table empty
        if self.check_empty_table(self.category_table) is None:
            self.insert_activity('Add Tasks on the Setup Tab', 'Double click to edit')
        
        # check if log table empty
        # add one dummy entry now with no elapsed time
        if self.check_empty_table(self.log_table) is None:
            self.insert_timestamp(1, start=datetime.now(), stop=datetime.now())


    def check_empty_table(self, table):
        """
        Method to check for empty tables
        If empty, returns None
        If items, returns first row
        """
        stmt = select(table)
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            return result.first()        
        

    def view_categories(self):
        """Method to return category table"""
        stmt = select(self.category_table)
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            return result.all()
    

    def insert_timestamp(self, activity, start, stop):
        """Method to insert log entry with activity and timestamps"""
        stmt = insert(self.log_table).values(taskid=activity, start=start, stop=stop)
        with self.engine.connect() as conn:
            conn.execute(stmt)
            conn.commit()
    

    def insert_activity(self, activity, category):
        """Method for adding new category to database"""
        stmt = insert(self.category_table).values(activity=activity, grouping=category)
        with self.engine.connect() as conn:
            conn.execute(stmt)
            conn.commit()
    

    def delete_activity(self, activity, category):
        """Method to delete cateogry from database"""
        stmt = delete(self.category_table).where(self.category_table.c.activity == activity, self.category_table.c.grouping == category)
        with self.engine.connect() as conn:
            conn.execute(stmt)
            conn.commit()

    
    def update_activity(self, old_activity, old_category, new_activity, new_category):
        """Method to update activity and category from database"""
        with self.engine.connect() as conn:
            conn.execute(
                update(self.category_table)
                .values(activity = new_activity, grouping = new_category)
                .where(self.category_table.c.activity == old_activity, self.category_table.c.grouping == old_category)
            )
            conn.commit()



class AnalysisGraphDFs:
    """
    Class to handle getting and graphing log dataframes
    Use same db instance for main app to keep sqlalchemy engine and metadata consistent
    This technique looks like it works, need to add some better variable matchup to keep
    files consistent

    To Do
        ValueError for ordering days of week. Seems to reorder data in df instead of generally setting levels
    
    """

    def __init__(self, db_instance):
        self.db_instance = db_instance

        # take values from SQLAlchemyDB instance
        self.engine = self.db_instance.engine
        self.meta = self.db_instance.meta
        self.log = self.db_instance.log_table
        self.category = self.db_instance.category_table

        
    def get_log_df(self):
        """Method to get initial log df"""
        df = None
        stmt = select(self.log.c.id, self.category.c.activity, self.category.c.grouping, self.log.c.start, self.log.c.stop).where(self.log.c.taskid == self.category.c.id)

        with self.engine.connect() as conn:
            result = conn.execute(stmt).all()
            df = pd.DataFrame(result)

        # df cleanup
        df['duration'] = df['stop'] - df['start']
        df['date'] = df['start'].dt.date
        df['DayOfWeek'] = df['start'].dt.day_name()

        # get duration of total seconds as int for converstion to unrestricted hours hh:mm:ss formatting
        df['seconds_duration'] = df['duration'] / np.timedelta64(1, 's')
        df['seconds_duration'] = df['seconds_duration'].round()
        df['seconds_duration'] = df['seconds_duration'].astype(dtype='int64')

        return df
    
    
    def get_df_log_summary(self):
        """Returns df for log tab with data aggreated by day"""
        self.log_df = None
        self.log_df = self.get_log_df()

        # group by day and day of week
        df_grouping = self.log_df.groupby(['date', 'DayOfWeek'], as_index=False)

        # add total seconds to get unrestricted hh:mm:ss
        df_log_summary = df_grouping['seconds_duration'].sum()
        df_log_summary['hms_duration'] = df_log_summary['seconds_duration'].apply(TimerFuncs.get_time_hms)

        df_log_summary['DayOfWeek'] = df_log_summary['DayOfWeek'].astype('category')

        # try for dealing with database that doesn't have full range of entries with all the weekdays present
        try:
            df_log_summary['DayOfWeek'] = df_log_summary['DayOfWeek'].cat.reorder_categories(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
        except ValueError as e:
            print(e)
        
        df_log_summary = df_log_summary[['date', 'DayOfWeek', 'hms_duration']]

        return df_log_summary


    def get_df_log_summary_weeks(self):
        """Retuns df for log tab with durations aggrgated and summed per week"""
        df = None
        df = self.get_log_df()

        # week start, starts on Monday
        df['week_start'] = df['start'] - df['start'].dt.weekday.astype('timedelta64[D]')
        df['week_start'] = df['week_start'].dt.date

        # week grouping and summation of total hh:mm:ss
        df_week_grouping = df.groupby(['week_start'], as_index=False)
        df_week_summary = df_week_grouping['seconds_duration'].sum()
        df_week_summary['hms_duration'] = df_week_summary['seconds_duration'].apply(TimerFuncs.get_time_hms)

        # hardcoded Monday start of week, might change to programatic approach
        df_week_summary['day'] = 'Monday'
        df_week_summary = df_week_summary[['week_start', 'day', 'hms_duration']]

        return df_week_summary


    def get_df_log_summary_months(self):
        """Returns df for log tab with durations aggregated and summed per month"""
        df = None
        df = self.get_log_df()

        # generate two columns
        df['year_month'] = df['start'].dt.strftime('%Y %m')
        df['month_name'] = df['start'].dt.strftime('%b')

        # grouping and summation of total seconds for unrestricted hh:mm:ss
        df_month_grouping = df.groupby(['year_month', 'month_name'], as_index=False)
        df_month_summary = df_month_grouping['seconds_duration'].sum()
        df_month_summary['hms_duration'] = df_month_summary['seconds_duration'].apply(TimerFuncs.get_time_hms)

        df_month_summary = df_month_summary[['year_month', 'month_name', 'hms_duration']]

        return df_month_summary

    
    def get_df_summary(self, days=7):
        """Method to make df summary for graphing"""
        self.log_df = self.get_log_df()
        df_grouping = self.log_df.groupby(['date', 'DayOfWeek'], as_index=False)
        df_summary = df_grouping['duration'].sum()
        # convert duration from timedelta to float hours
        df_summary['duration'] = df_summary['duration'] / np.timedelta64(1, 'h')
        df_summary['DayOfWeek'] = df_summary['DayOfWeek'].astype('category')
        # find another way to organize categories, if all days of the week aren't there, then throws value error
        # just bypassing at moment, need better solution
        try:
            df_summary['DayOfWeek'] = df_summary['DayOfWeek'].cat.reorder_categories(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
        except ValueError as e:
            print(e)

        if days == 7:
            filt = df_summary['date'] >= TimeDeltaDays.last_seven_days()
            df_plot = df_summary[filt]
        elif days == 30:
            filt = df_summary['date'] >= TimeDeltaDays.last_thirty_days()
            df_plot = df_summary[filt]
        else:
            df_plot = df_summary

        return df_plot

