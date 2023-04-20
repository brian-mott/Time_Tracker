Create productive time goals and track progress over days, weeks, and months

A timer app used to track productive time towards a daily goal One timer counts down towards the daily goal and a stopwatch counts up for amount of time spent on a given task

The user can change the daily countdown goal, edit categories of activities, and see graphed results over time regarding time spent per day and weekly averages

Logic

The timers track total seconds; these are converted to hh:mm:ss for easy interpretation
Each start and pause generates a timestamp. This timestamp and the selected activity are saved to a sqlite3 database
Database schema:
    log table that records timestamps and activities
    categories table to normalize activities and their category grouping
Time data can then be aggregated and summed in various ways for analysis and graphing
    Dataframes are used for aggregating
    Graphing done with matplotlib 
main_app for frames and windows datetimefuncs with classes that handle conversion from seconds to hh:mm:ss; calculating last 7 or 30 days for df filtering dbsanddfs with classes for SQLalchemy db setup and manipulaiton of df for graphing and logging

UI layout: 4 main tabs: Timer Graphs/Analysis Log Setup Each tab is its own frame Graph/Analysis frame contains placeholder frame at location where graph objects are displayed Frames are packed into tabs Grids for finer frame layout

Graphing handled within the Analysis frame class