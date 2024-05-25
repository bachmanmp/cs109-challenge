# -*- coding: utf-8 -*-
"""CS109 Challenge.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1XfMJuXbC_xp3PSfDhZ0zznaD5623AEFa
"""

!pip install gmplot
!pip install pandas
!pip install datetime

from heapq import nlargest
import datetime
import gmplot
import os
import pandas as pd
import random as random
import time
import sys

# Datasource references (Santa Clara County, City of San Jose):
# Public schools:  https://data-sccphd.opendata.arcgis.com/datasets/e19dc214fb8b451788df878272bb4cea_0/explore
# Car crashes:  https://data.sanjoseca.gov/dataset/crashes-data

# Global dicts for use across methods
counts_dict = {"Days" : 0, "Crashes" : 0, "Injuries" : 0, "Fatalities": 0, "Speeding": 0, "HitandRun": 0, "Car": 0, "Bike" : 0, "Pedestrian": 0, "CarInjuries" : 0, "CarFatalities": 0, "BikeInjuries" : 0, "BikeFatalities": 0, "CrashNearSchool": 0}
school_crash_dict = {}
school_bike_dict = {}
weather_count = {}
weather_crash_info= {}
weather_prob_dict = {}
visibility_info = {}
visibility_count = {}
visibility_prob_dict = {}
weather_visib_count_dict = {}
weather_visib_prob_dict = {}
lambda_predictions = {}

# Global dicts for intersection and roads
intersection_dict = {}
road_dict = {}
bike_intersection_dict = {}
bike_road_dict = {}

# read each datasource into a dataframe
schools = pd.read_csv("/content/drive/MyDrive/cs109/data/schools.csv")
crashes_sorted = pd.read_csv("/content/drive/MyDrive/cs109/data/crashes_data.csv").sort_values(by="CrashDateTime", ascending=True)
crashes_filtered = []

# first, populate all the dicts, then determine crashes by schools, create Google Maps and then crunch stats
def main():
  populate_general_counts()
  crashes_near_schools()
  create_maps_visual("Car")
  create_maps_visual("Bike")
  print_stats()
  evaluations("/content/drive/MyDrive/cs109/data/crashes_test.csv")

# go through and populate the dicts
def populate_general_counts():
  print("Crunching dataset")

  # get consistent datetime formats
  date = datetime.date.fromtimestamp(time.time())
  counts_dict["Days"] = (datetime.datetime.now() - convert_to_datetime(crashes_sorted.iloc[2].CrashDateTime, '%m/%d/%Y %I:%M:%S %p')).days

  total_crashes = 0
  for row in crashes_sorted.itertuples():

    # process road and intersection data
    road_dict[row.AStreetName] = road_dict.get(row.AStreetName, 0) + 1
    road_dict[row.BStreetName] = road_dict.get(row.BStreetName, 0) + 1
    intersection_dict[str(row.AStreetName) + "," + str(row.BStreetName)] = intersection_dict.get(str(row.AStreetName) + "," + str(row.BStreetName), 0) + 1

    # drop events where we do not have enough information
    if row.Lighting == "Unknown" or row.RoadwaySurface == "Unknown" or row.Weather == "Other" or row.Weather == "Unknown":
      continue
    else:
      crashes_filtered.append(row)
      if convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p') < datetime.datetime.now():
        total_crashes += 1

      if row.Injuries >0:
        counts_dict["Injuries"] += row.Injuries
        if row.VehicleInvolvedWith == "Bike" or row.VehicleInvolvedWith == "Pedestrian":
          counts_dict["BikeInjuries"] += row.Injuries
        else:
          counts_dict["CarInjuries"] += row.Injuries

      if row.FatalInjuries > 0:
        counts_dict["Fatalities"] += row.FatalInjuries
        if row.VehicleInvolvedWith == "Bike" or row.VehicleInvolvedWith == "Pedestrian":
          counts_dict["BikeFatalities"] += row.FatalInjuries
        else:
          counts_dict["CarFatalities"] += row.FatalInjuries

      if row.VehicleInvolvedWith == "Bike":
        counts_dict["Bike"] += 1

        # process road data
        bike_road_dict[row.AStreetName] = bike_road_dict.get(row.AStreetName, 0) + 1
        bike_road_dict[row.BStreetName] = bike_road_dict.get(row.BStreetName, 0) + 1
        bike_intersection_dict[str(row.AStreetName) + "," + str(row.BStreetName)] = bike_intersection_dict.get(str(row.AStreetName) + "," + str(row.BStreetName), 0) + 1

      elif row.VehicleInvolvedWith == "Pedestrian":
        counts_dict["Pedestrian"] += 1

         # process road data
        bike_road_dict[row.AStreetName] = bike_road_dict.get(row.AStreetName, 0) + 1
        bike_road_dict[row.BStreetName] = bike_road_dict.get(row.BStreetName, 0) + 1
        bike_intersection_dict[str(row.AStreetName) + "," + str(row.BStreetName)] = bike_intersection_dict.get(str(row.AStreetName) + "," + str(row.BStreetName), 0) + 1
      else:
        counts_dict["Car"] += 1

      if row.SpeedingFlag == True:
        counts_dict["Speeding"] += 1

      if row.HitAndRunFlag == True:
        counts_dict["HitandRun"] += 1

      date = convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p')
      date = date.strftime("%Y-%m-%d")
      weather_count[date] = row.Weather

      visibility = row.Lighting
      if "Dark" in str(row.Lighting) or "Dusk" in str(row.Lighting):
        visibility = "Dark"
      elif "Daylight" in str(row.Lighting):
        visibility = "Daylight"
      else:
        visibility = "Unknown"

        # check the time of the crash to determine
        if convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p').hour >= 7 and convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p').hour < 19:
          visibility = "Daylight"
        else:
          visibility = "Dark"

      visibility_count[date] = visibility
      counts_dict["Crashes"] = total_crashes

# go through and determine crashes near schools and vehicle involvement
def crashes_near_schools():
  for crash in crashes_sorted.itertuples():
    for school in schools.itertuples():
      # check distance of crash to each school and if its under quarter-mile
      if (abs(school.LATITUDE - crash.Latitude)) <= quarter_mile_latitude_diff():
        counts_dict["CrashNearSchool"] += 1
        # get crash information
        school_crash_dict[school.PLACENAME] = school_crash_dict.get(school.PLACENAME, 0) + 1

        # look for bike or pedestrian involvement
        if crash.VehicleInvolvedWith == "Bike" or crash.VehicleInvolvedWith == "Pedestrian":
          school_bike_dict[school.PLACENAME] = school_bike_dict.get(school.PLACENAME, 0) + 1

    # populate weather and visibility
    weather_crash_info[crash.Weather] = weather_crash_info.get(crash.Weather, 0) + 1

    visibility = crash.Lighting
    if "Dark" in str(crash.Lighting) or "Dusk" in str(crash.Lighting):
      visibility = "Dark"
    elif "Daylight" in str(crash.Lighting):
      visibility = "Daylight"
    else:
      visibility = "Unknown"

      # check the time of the crash to determine
      if convert_to_datetime(crash.CrashDateTime, '%m/%d/%Y %I:%M:%S %p').hour >= 7 and convert_to_datetime(crash.CrashDateTime, '%m/%d/%Y %I:%M:%S %p').hour < 19:
        visibility = "Daylight"
      else:
        visibility = "Dark"

    visibility_info[visibility] = visibility_info.get(visibility, 0) + 1

# utility method to convert to a consistent datetime
def convert_to_datetime(date_str, format):
    format_string = '%m/%d/%Y %I:%M:%S %p'
    datetime_obj = datetime.datetime.now()

    # Parse the date string into a datetime object
    if not isinstance(date_str, float):
      datetime_obj = datetime.datetime.strptime(date_str, format_string)

    return datetime_obj

# create a Bayesian network model for weather and visibilitiy given a crash
# calculate weather and visibility MLE rates
def create_bayesian_model():
  # populate weather bayesian nodes
  for weather in weather_crash_info:
    total_days_weather = sum(1 for v in weather_count.values() if v == weather)
    if total_days_weather > 0:
      weather_prob_dict[weather] = weather_crash_info[weather] / total_days_weather

  # populate visibility bayesian nodes
  for visibility in visibility_info:
    total_days_visibility = sum(1 for v in visibility_count.values() if v == visibility)
    if total_days_visibility > 0:
      visibility_prob_dict[visibility] = visibility_info[visibility] / total_days_visibility

  # now populate the joint matrix
  for crash in crashes_sorted.itertuples():
    visibility = crash.Lighting
    if "Dark" in str(crash.Lighting) or "Dusk" in str(crash.Lighting):
      visibility = "Dark"
      weather_visib_count_dict[crash.Weather, visibility] = weather_visib_count_dict.get((crash.Weather, visibility), 0) + 1
    elif "Daylight" in str(crash.Lighting):
      visibility = "Daylight"
      weather_visib_count_dict[crash.Weather, visibility] = weather_visib_count_dict.get((crash.Weather, visibility), 0) + 1

  for i in weather_visib_count_dict:
    weather_visib_prob_dict[i] = weather_visib_count_dict[i] / counts_dict["Days"]

  print("Joint Lambda")
  print(weather_visib_prob_dict)

# utilizing gmplot, create 2 Google Maps visuals to navigate school crash data
def create_maps_visual(involvement):
  GOOGLE_MAPS_API = "AIzaSyDXuQV55LuSJ1mzjRbNYa3dNrZYoCXhaos"
  gmap2 = gmplot.GoogleMapPlotter.from_geocode("San Jose, California", apikey="AIzaSyDXuQV55LuSJ1mzjRbNYa3dNrZYoCXhaos")

  if involvement == "Bike" or involvement == "Pedestrian":
    for school in school_bike_dict:

      # get school lat/long
      school_lat = schools[schools.PLACENAME == school].LATITUDE.values[0]
      school_long = schools[schools.PLACENAME == school].LONGITUDE.values[0]

      # get crash stats per school
      crash_count = school_bike_dict[school]

      # plot on map
      gmap2.circle(school_lat, school_long, radius=crash_count, color="blue")
      gmap2.marker(school_lat, school_long, title=school+" "+str(crash_count))

    gmap2.draw("bike_crashes.html")
    print("Generated Google Maps visual: bike_crashes.html")
  else:
    for school in school_crash_dict:

      # get school lat/long
      school_lat = schools[schools.PLACENAME == school].LATITUDE.values[0]
      school_long = schools[schools.PLACENAME == school].LONGITUDE.values[0]

      # get crash stats per school
      crash_count = school_crash_dict[school]

      # plot on map
      gmap2.circle(school_lat, school_long, radius=crash_count, color="red")
      gmap2.marker(school_lat, school_long, title=school+" "+str(crash_count))

    gmap2.draw("car_crashes.html")
    print("Generated Google Maps visual: car_crashes.html")

# utility method to calculate a quarter mile from a latitude
def quarter_mile_latitude_diff():
    earth_circumference = 24901  # miles
    degrees_latitude = 360
    distance_per_degree = earth_circumference / degrees_latitude  # miles/degree
    quarter_mile = 0.25  # miles
    latitude_diff = quarter_mile / distance_per_degree  # degrees

    return latitude_diff

def filter_crash_visibility_list(value, crashes):
  filtered_crashes = []
  for crash in crashes.itertuples():
    if value in str(crash.Lighting):
      filtered_crashes.append(crash)
  return pd.DataFrame(filtered_crashes)

# calculate the pvalue for visibility (Daylight, Dark)
def visibility_pvalue_boot(value1, value2):
  value1_count = visibility_filtering_function(value1, value2, crashes_sorted)[1]
  value2_count = visibility_filtering_function(value1, value2, crashes_sorted)[2]
  value1_crash_list = filter_crash_visibility_list(value1, crashes_sorted)
  value2_crash_list = filter_crash_visibility_list(value2, crashes_sorted)
  uniform = value1_crash_list + value2_crash_list
  observed_diff = visibility_filtering_function(value1, value2, uniform)[0]

  count = 0
  for i in range(10000):
    value1_boot = uniform.sample(len(value1_crash_list), replace=True)
    value2_boot = uniform.sample(len(value2_crash_list), replace=True)

    value1_mean = visibility_filtering_function(value1, value2, value1_boot)[1]/len(value1_boot)
    value2_mean = visibility_filtering_function(value1, value2, value2_boot)[2]/len(value2_boot)
    boot_diff = value1_mean - value2_mean
    if boot_diff > observed_diff:
      count += 1
  return count / 10000

# filter the crash list for particular visibility details and get the diff of means
def visibility_filtering_function(value1, value2, crash_list):
  value1_count = 0
  value2_count = 0
  for i in crash_list.itertuples():
    if value1 in str(i.Lighting):
      value1_count += 1
    elif value2 in str(i.Lighting):
      value2_count += 1
  return abs((value1_count/len(crash_list)) - (value2_count/len(crash_list))), value1_count, value2_count

def filter_crash_weather_list(value, crashes):
  filtered_crashes = []
  for crash in crashes.itertuples():
    if value in str(crash.Weather):
      filtered_crashes.append(crash)
  return pd.DataFrame(filtered_crashes)

# calculate the pvalue for weather (Clear, Rain)
def weather_pvalue_boot(value1, value2):
  value1_count = weather_filtering_function(value1, value2, crashes_sorted)[1]
  value2_count = weather_filtering_function(value1, value2, crashes_sorted)[2]
  value1_crash_list = filter_crash_weather_list(value1, crashes_sorted)
  value2_crash_list = filter_crash_weather_list(value2, crashes_sorted)
  uniform = value1_crash_list + value2_crash_list
  observed_diff = weather_filtering_function(value1, value2, uniform)[0]

  count = 0
  for i in range(10000):
    value1_boot = uniform.sample(len(value1_crash_list), replace=True)
    value2_boot = uniform.sample(len(value2_crash_list), replace=True)

    value1_mean = weather_filtering_function(value1, value2, value1_boot)[1]/len(value1_boot)
    value2_mean = weather_filtering_function(value1, value2, value2_boot)[2]/len(value2_boot)
    boot_diff = value1_mean - value2_mean
    if boot_diff > observed_diff:
      count += 1
  return count / 10000

# filter the crash list for particular weather details and get the diff of means
def weather_filtering_function(value1, value2, crash_list):
  value1_count = 0
  value2_count = 0
  for i in crash_list.itertuples():
    if value1 in str(i.Weather):
      value1_count += 1
    elif value2 in str(i.Weather):
      value2_count += 1
  return abs((value1_count/len(crash_list)) - (value2_count/len(crash_list))), value1_count, value2_count

# calculate the pvalue for vehicle involvement (Car, Bike+Pedestrian)
def vehicle_pvalue(category):
  value1_count = counts_dict["Car"]
  value2_count = counts_dict["Bike"] + counts_dict["Pedestrian"]
  observed_diff = abs((counts_dict["Car"+str(category)] / counts_dict["Car"]) - (counts_dict["Bike"+str(category)] / (counts_dict["Bike"] + counts_dict["Pedestrian"])))

  count = 0
  for i in range(10000):
    value1_boot = crashes_sorted.sample(value1_count, replace=True)
    value2_boot = crashes_sorted.sample(value2_count, replace=True)

    value1_mean = filter_vehicle_involvement(category, "Car", value1_boot)
    value2_mean = filter_vehicle_involvement(category, "Bike", value2_boot) + filter_vehicle_involvement(category, "Pedestrian", value2_boot)
    boot_diff = abs(value1_mean - value2_mean)
    if boot_diff > observed_diff:
      count += 1
  return count / 10000

# filter utility to get the mean of vehicle involvement in dataset
def filter_vehicle_involvement(category, vehicle, data):
  count = 0
  for i in data.itertuples():
    if category == "Fatalities":
      if i.FatalInjuries > 0:
        if vehicle == "Car":
          if "Bike" not in str(i.VehicleInvolvedWith) or "Pedestrian" not in str(i.VehicleInvolvedWith):
            count += 1
        else:
          if vehicle in str(i.VehicleInvolvedWith):
            count += 1
    else:
      if i.Injuries > 0:
        if vehicle == "Car":
          if "Bike" not in str(i.VehicleInvolvedWith) or "Pedestrian" not in str(i.VehicleInvolvedWith):
            count += 1
        else:
          if vehicle in str(i.VehicleInvolvedWith):
            count += 1
  return count/len(data)

def calculate_pvalues():
  print("p-value (Daylight vs. Dark): ", visibility_pvalue_boot("Daylight", "Dark"))
  print("p-value (Clear vs. Rain): ", weather_pvalue_boot("Clear", "Rain"))
  print("p-value (Car vs. Bike+Pedestrian Injuries): ", vehicle_pvalue("Injuries"))
  print("p-value (Car vs. Bike+Pedestrian Fatalities): ", vehicle_pvalue("Fatalities"))

def print_stats():
  # crashes per day lambda
  crash_lambda = counts_dict["Crashes"] / counts_dict["Days"]
  bike_lambda = (counts_dict["Bike"] + counts_dict["Pedestrian"]) / counts_dict["Days"]

  lambda_predictions["Crashes"] = crash_lambda
  lambda_predictions["Bike"] = bike_lambda

  print("Summary Stats")
  print("Time Period for Analysis (in Days): ", counts_dict["Days"])
  print("Time Period for each Lambda:  day")
  print("---------------")
  print("Maximum Likelihood Estimation (Car, Bike, Pedestrian Crash Rates)")
  print("Overall Car Crash Lambda: ", crash_lambda)
  print("Overall Bike/Pedestrian Involvement Lambda: ", bike_lambda)
  create_bayesian_model()

  print("---------------")
  print("Bayesian Network (Weather & Visibility Crash Rates)")
  print("Weather Crash Rates (Lambda)")
  print(weather_prob_dict)

  for i in weather_visib_prob_dict:
    lambda_predictions[i] = weather_visib_prob_dict[i]

  print("Visibility Crash Rates (Lambda)")
  print(visibility_prob_dict)

  for j in visibility_prob_dict:
    lambda_predictions[j] = visibility_prob_dict[j]

  print("---------------")
  print("Car Injuries & Fatalities")
  print("Car Injury %: ", counts_dict["CarInjuries"] / counts_dict["Car"])
  print("Car Fatality %: ", counts_dict["CarFatalities"] / counts_dict["Car"])

  lambda_predictions["CarInjuries"] = counts_dict["CarInjuries"] / counts_dict["Days"]
  lambda_predictions["CarFatalities"] = counts_dict["CarFatalities"] / counts_dict["Days"]

  print("Bike Injuries & Fatalities")
  print("Bike+Pedestrian Injury %: ", counts_dict["BikeInjuries"] / (counts_dict["Bike"] + counts_dict["Pedestrian"]))
  print("Bike+Pedestrian Fatality %: ", counts_dict["BikeFatalities"] / (counts_dict["Bike"] + counts_dict["Pedestrian"]))

  lambda_predictions["BikeInjuries"] = counts_dict["BikeInjuries"] / counts_dict["Days"]
  lambda_predictions["BikeFatalities"] = counts_dict["BikeFatalities"] / counts_dict["Days"]
  lambda_predictions["Injuries"] = counts_dict["Injuries"] / counts_dict["Days"]
  lambda_predictions["Fatalities"] = counts_dict["Fatalities"] / counts_dict["Days"]

  print("---------------")
  print("Speeding")
  print(counts_dict["Speeding"] / counts_dict["Crashes"])
  print("Hit and Run")
  print(counts_dict["HitandRun"] / counts_dict["Crashes"])

  print("---------------")
  print("p-values")
  print("Grab a coffee (10000 samples of a 8000 row list, 8 variables, eta 45mins)")
  calculate_pvalues()

  print("---------------")
  print("Top 10 schools to look at traffic patterns and safety")
  print("School Crash Statistics")
  print(nlargest(10, school_crash_dict.items(), key=lambda x: x[1]))
  print("School Bike Statistics")
  print(nlargest(10, school_bike_dict.items(), key=lambda x: x[1]))

  print("---------------")
  print("Top 10 roads and intersections to look at traffic patterns and safety")
  print(nlargest(10, road_dict.items(), key=lambda x: x[1]))
  print(nlargest(10, intersection_dict.items(), key=lambda x: x[1]))

  print("---------------")
  print("Top 10 roads and intersections to look at for bike/pedestrian safety")
  print(nlargest(10, bike_road_dict.items(), key=lambda x: x[1]))
  print(nlargest(10, bike_intersection_dict.items(), key=lambda x: x[1]))

def evaluations(test_data):
  test_data = pd.read_csv(test_data)
  test_data_filtered = []

  # get consistent datetime formats
  date = datetime.date.fromtimestamp(time.time())
  test_dict = {"Days" : 0, "Crashes" : 0, "Injuries" : 0, "Fatalities": 0, "Speeding": 0, "HitandRun": 0, "Car": 0, "Bike" : 0, "Pedestrian": 0, "CarInjuries" : 0, "CarFatalities": 0, "BikeInjuries" : 0, "BikeFatalities": 0, "CrashNearSchool": 0}
  weather_test_count = {}
  visibility_test_count = {}
  test_dict["Days"] = (datetime.datetime.now() - convert_to_datetime(test_data.iloc[2].CrashDateTime, '%m/%d/%Y %I:%M:%S %p')).days
  testing_days = test_dict["Days"]

  total_crashes = 0
  for row in test_data.itertuples():

    # drop events where we do not have enough information
    if row.Lighting == "Unknown" or row.RoadwaySurface == "Unknown" or row.Weather == "Other" or row.Weather == "Unknown":
      continue
    else:
      test_data_filtered.append(row)
      if convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p') < datetime.datetime.now():
        total_crashes += 1

      if row.Injuries >0:
        test_dict["Injuries"] += row.Injuries
        if row.VehicleInvolvedWith == "Bike" or row.VehicleInvolvedWith == "Pedestrian":
          test_dict["BikeInjuries"] += row.Injuries
        else:
          test_dict["CarInjuries"] += row.Injuries

      if row.FatalInjuries > 0:
        test_dict["Fatalities"] += row.FatalInjuries
        if row.VehicleInvolvedWith == "Bike" or row.VehicleInvolvedWith == "Pedestrian":
          test_dict["BikeFatalities"] += row.FatalInjuries
        else:
          test_dict["CarFatalities"] += row.FatalInjuries

      if row.VehicleInvolvedWith == "Bike":
        test_dict["Bike"] += 1
      elif row.VehicleInvolvedWith == "Pedestrian":
        test_dict["Pedestrian"] += 1
      else:
        test_dict["Car"] += 1

      if row.SpeedingFlag == True:
        test_dict["Speeding"] += 1

      if row.HitAndRunFlag == True:
        test_dict["HitandRun"] += 1

      date = convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p')
      date = date.strftime("%Y-%m-%d")
      weather_test_count[date] = row.Weather

      visibility = row.Lighting
      if "Dark" in str(row.Lighting) or "Dusk" in str(row.Lighting):
        visibility = "Dark"
      elif "Daylight" in str(row.Lighting):
        visibility = "Daylight"
      else:
        visibility = "Unknown"

        # check the time of the crash to determine
        if convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p').hour >= 7 and convert_to_datetime(row.CrashDateTime, '%m/%d/%Y %I:%M:%S %p').hour < 19:
          visibility = "Daylight"
        else:
          visibility = "Dark"

      visibility_test_count[date] = visibility
      test_dict["Crashes"] = total_crashes

  print("---------------")
  print("Evaluations over ", testing_days, " days (% over 1 is over prediction)")
  print("Car Crash Count Accuracy: ", lambda_predictions["Crashes"]*testing_days/test_dict["Crashes"])
  print("Bike Crash Count Accuracy: ", lambda_predictions["Bike"]*testing_days/test_dict["Bike"])
  print("Injuries Accuracy: ", lambda_predictions["Injuries"]*testing_days/test_dict["Injuries"])
  print("Fatalities Accuracy: ", lambda_predictions["Fatalities"]*testing_days/test_dict["Fatalities"])

if __name__ == '__main__':
  main()