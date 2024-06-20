
rm(list=ls())
gc()


library(arrow)
library(dataverse)
library(tidyverse)
library("writexl")

Sys.setenv("DATAVERSE_SERVER" = "https://dataverse.harvard.edu",
           "DATAVERSE_KEY" = "2d0a656a-5292-4a78-8415-3cbaeb11bde3")

meetings = data.frame()

for(year in 2020:2023){
  
  print(year)
  
  long = get_dataframe_by_name(filename = paste0("meetings.", year, ".parquet"),
                               dataset = "10.7910/DVN/NJTBEM",
                               .f = arrow::read_parquet)
  long = long %>% filter( state_name == "Florida")
  # short = long %>% dplyr::select( state_name, place_name, vid_id, meeting_date, vid_upload_date )
  meetings = rbind( meetings, long )
  
}

write_csv( meetings, "../../../6. Data/Localview/localview_florida.csv" ) # Excel
