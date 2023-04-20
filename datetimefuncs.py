"""
Classes with static methods for converting time values and
displaying hh:mm:ss formatting when needed

Can be standalone funcs but trying classes for better organization
"""

from math import floor
from datetime import date, timedelta


class TimerFuncs:
    """Basic functions for formatting and converting timer values"""

    @staticmethod
    def formatted_time(total_seconds: int) -> str:
        """Input int of total seconds and return formatted string of hh:mm:ss"""
        hours = floor(total_seconds / 60 / 60) % 24
        minutes = floor(total_seconds / 60) % 60
        seconds = total_seconds % 60
        return f'{hours:02}:{minutes:02}:{seconds:02}'
    

    @staticmethod
    def get_total_seconds(hours: int, minutes: int, seconds: int) -> int:
        """Input ints of hours, min, sec and get int of total seconds"""
        return hours * 3600 + minutes * 60 + seconds
    

    @staticmethod
    def get_time_hms(total_seconds: int) -> str:
        """
        Takes int of total seconds and returns str with hours, minutes, seconds
        No upper limit for hours, will not rollover into another day
        Use with aggregated sums of total time per week or month
        """
        hours = floor(total_seconds / 60 / 60)
        minutes = floor(total_seconds / 60) % 60
        seconds = total_seconds % 60

        return f'{hours:02}:{minutes:02}:{seconds:02}'



class TimeDeltaDays:
    """
    Static methods to calculate time period for last seven days
    and last thirty days
    """
    @staticmethod
    def last_seven_days():
        return date.today() - timedelta(days=7)


    @staticmethod
    def last_thirty_days():
        return date.today() - timedelta(days=30)