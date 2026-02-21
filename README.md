# Global Climate Indicators Dashboard

A Streamlit-based dashboard for exploring global climate indicators using interactive visualizations and time-series analysis.

---

## Overview

This project provides an interactive interface to analyze climate-related data across years and countries.

The dashboard allows users to:

- Filter data by year range  
- Compare countries across climate indicators  
- View long-term trends  
- Analyze correlations between variables  
- Export filtered datasets and charts  

---

## Features

- CSV dataset ingestion with automatic separator detection  
- Automatic column detection using keyword matching  
- Global KPI summaries (latest year in range)  
- Multi-line time-series visualization  
- Rolling average smoothing  
- Optional normalization (0–1 scaling)  
- Decade-based faceted charts  
- Country comparison plots  
- Choropleth world map visualization  
- Correlation heatmap  
- CSV and PNG export functionality  

---

## Supported Indicators

Primary indicators:
- Temperature Anomaly  
- CO₂ Emissions  
- Sea Level Rise  

Secondary indicators (if available in dataset):
- Arctic Ice Extent  
- Ocean Acidification  
- Renewable Energy Usage  
- Deforestation Rate  
- Biodiversity Index  
- Per Capita Emissions  
- Air Pollution Index  

The application adapts automatically depending on which columns are present in the dataset.

---

## Tech Stack

- Python  
- Streamlit  
- Pandas  
- NumPy  
- Plotly  

---
