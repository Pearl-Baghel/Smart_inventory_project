# Smart Inventory and Supply Risk Dashboard for Namaste LA

## Overview
This project presents a **data-driven inventory planning and supply risk dashboard** designed for **Namaste LA**, a small cloud kitchen that sells fresh vegetarian food at weekend farmers markets in Southern California. The system helps improve planning for perishable products by connecting **sales data, demand forecasting, ingredient requirements, inventory evaluation, and purchase recommendations** into one structured workflow.

The main goal is to reduce waste, prevent stockouts, and support smarter purchasing decisions using a practical solution built with **Python, Excel, and Streamlit**.

## Problem Statement
Like many small food businesses, Namaste LA faced challenges such as:
- High food waste caused by overproduction
- Stockouts during peak demand periods
- Inefficient and reactive purchasing decisions
- Limited visibility into demand, inventory, and ingredient needs

Because food is prepared before the market weekend begins, inaccurate planning directly affects both cost and customer satisfaction.

## Solution
The dashboard transforms historical sales data into weekly operational decisions through the following flow:

**Sales Data -> Forecast -> Requirements -> Inventory Check -> Purchase Plan -> Dashboard**

### Core Functions
- Forecast weekly item-level demand
- Convert forecasts into ingredient and packaging requirements using recipe BOMs
- Compare requirements with current inventory
- Generate recommended purchase quantities with safety stock consideration
- Track waste as a feedback mechanism for future planning
- Provide an interactive dashboard for decision support

## Tools and Technologies
- **Python** for data cleaning, validation, forecasting, and purchase planning
- **Excel** for exploratory analysis, inventory modeling, and what-if analysis
- **Streamlit** for dashboard visualization and user interaction
- Forecasting approaches include **Moving Average**, **Croston's Method**, and **Prophet** depending on demand behavior

## Project Highlights
- Built for a **small food business environment** with limited resources and high demand uncertainty
- Uses a **component-level inventory approach** instead of only item-level planning
- Supports both **operational efficiency** and **sustainability goals**
- Includes a supplementary **what-if profit optimization analysis** in Excel using Solver

## Reported Impact
Based on project findings, the system helped:
- Reduce food waste from about **50%** to roughly **15-25%**
- Improve product availability by reducing stockouts
- Support more consistent and structured decision-making
- Improve cost control and weekly purchasing efficiency

## Suggested Repository Structure
```text
project/
├── app.py
├── raw_to_sales_clean.py
├── ingest_validate.py
├── weekly_forecast.py
├── planning_requirements.py
├── data/
├── outputs/
├── dashboard_assets/
└── README.md
```

## Future Improvements
- Add weather and event-based demand signals
- Integrate directly with a point-of-sale system
- Expand to multiple locations or a larger menu
- Add low-inventory alerts and advanced scenario analysis

## Author
**Pearl Baghel** 
