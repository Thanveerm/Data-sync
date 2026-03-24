# Data Sync Server Module

## Overview
This module enables synchronization of `account.analytic.line` data from one Odoo server to another based on date range selection.

## Features
- Configure source and target server connections
- Sync data based on create_date range (start date to end date)
- Automatic field mapping and related record resolution
- Connection testing for both source and target servers
- Detailed sync logs with success/failure tracking
- Support for related fields (project, task, employee, etc.)

## Installation
1. Copy the module to your Odoo addons directory
2. Update the app list
3. Install "Data Sync Server" module

## Configuration
1. Go to **Data Sync > Sync Configurations**
2. Create a new configuration:
   - **Configuration Name**: Give it a descriptive name
   - **Source Server**: Enter URL, database name, username, and password
   - **Target Server**: Enter URL, database name, username, and password
3. Click **Test Source Connection** and **Test Target Connection** to verify

## Usage
1. Open a sync configuration
2. Click **Sync Data** button
3. Select **Start Date** and **End Date** for the records you want to sync
4. Click **Start Sync**
5. Monitor the sync log for progress and results

## Technical Details
- Model synced: `account.analytic.line`
- Date filter: Based on `create_date` field
- Fields synced: name, date, unit_amount, project_id, task_id, employee_id, company_id, currency_id, amount, account_id, department_id, tag_ids
- Related records are matched by name in the target server

## Requirements
- Odoo 16.0
- XML-RPC access enabled on both source and target servers
- Required modules: base, analytic, hr_timesheet

## Notes
- Ensure related records (projects, tasks, employees, etc.) exist in the target server with matching names
- The module uses XML-RPC for communication between servers
- Sync is based on create_date, not write_date
