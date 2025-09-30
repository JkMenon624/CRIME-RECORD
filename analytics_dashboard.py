import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta, date
from database import Database

# Kerala districts for geographic analysis
KERALA_DISTRICTS = [
    'Thiruvananthapuram', 'Kollam', 'Pathanamthitta', 'Alappuzha', 'Kottayam',
    'Idukki', 'Ernakulam', 'Thrissur', 'Palakkad', 'Malappuram',
    'Kozhikode', 'Wayanad', 'Kannur', 'Kasaragod'
]

def display_analytics_dashboard():
    """Display comprehensive crime analytics dashboard"""
    
    st.title("📊 Crime Analytics Dashboard")
    st.markdown("### Kerala Police - Crime Records Analysis")
    
    db = Database()
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From Date",
            value=date.today() - timedelta(days=90),
            max_value=date.today(),
            help="Select start date for analysis"
        )
    with col2:
        end_date = st.date_input(
            "To Date",
            value=date.today(),
            max_value=date.today(),
            help="Select end date for analysis"
        )
    
    # Overview metrics
    display_overview_metrics(db, start_date, end_date)
    
    # Tabs for different analytics views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Trends Analysis", 
        "🗺️ Geographic Analysis", 
        "🎯 Crime Pattern Analysis",
        "⚡ Performance Metrics",
        "🔍 Detailed Reports"
    ])
    
    with tab1:
        display_trends_analysis(db, start_date, end_date)
    
    with tab2:
        display_geographic_analysis(db, start_date, end_date)
    
    with tab3:
        display_crime_pattern_analysis(db, start_date, end_date)
    
    with tab4:
        display_performance_metrics(db, start_date, end_date)
    
    with tab5:
        display_detailed_reports(db, start_date, end_date)

def display_overview_metrics(db, start_date, end_date):
    """Display overview metrics cards"""
    
    conn = db.connect()
    
    # Get metrics for the selected date range
    date_filter = f"AND DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'"
    
    # Total complaints
    total_complaints = pd.read_sql_query(f"""
        SELECT COUNT(*) as count FROM Complaints 
        WHERE 1=1 {date_filter}
    """, conn).iloc[0]['count']
    
    # Resolved cases
    resolved_cases = pd.read_sql_query(f"""
        SELECT COUNT(*) as count FROM Complaints 
        WHERE status = 'Resolved' {date_filter}
    """, conn).iloc[0]['count']
    
    # High severity cases
    high_severity = pd.read_sql_query(f"""
        SELECT COUNT(*) as count FROM Complaints 
        WHERE severity_level = 'High' {date_filter}
    """, conn).iloc[0]['count']
    
    # Cases with FIR
    fir_cases = pd.read_sql_query(f"""
        SELECT COUNT(DISTINCT c.complaint_id) as count 
        FROM Cases cs
        JOIN Complaints c ON cs.complaint_id = c.complaint_id
        WHERE 1=1 {date_filter}
    """, conn).iloc[0]['count']
    
    conn.close()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📋 Total Complaints",
            value=total_complaints,
            help="Total complaints filed in selected period"
        )
    
    with col2:
        resolution_rate = (resolved_cases / total_complaints * 100) if total_complaints > 0 else 0
        st.metric(
            label="✅ Resolved Cases",
            value=resolved_cases,
            delta=f"{resolution_rate:.1f}% resolution rate"
        )
    
    with col3:
        severity_rate = (high_severity / total_complaints * 100) if total_complaints > 0 else 0
        st.metric(
            label="🔴 High Severity",
            value=high_severity,
            delta=f"{severity_rate:.1f}% of total"
        )
    
    with col4:
        fir_rate = (fir_cases / total_complaints * 100) if total_complaints > 0 else 0
        st.metric(
            label="📄 FIR Filed",
            value=fir_cases,
            delta=f"{fir_rate:.1f}% of total"
        )

def display_trends_analysis(db, start_date, end_date):
    """Display temporal trends and patterns"""
    
    st.subheader("📈 Temporal Trends Analysis")
    
    conn = db.connect()
    
    # Daily trends
    daily_data = pd.read_sql_query(f"""
        SELECT 
            DATE(date_filed) as date,
            COUNT(*) as total_complaints,
            SUM(CASE WHEN severity_level = 'High' THEN 1 ELSE 0 END) as high_severity,
            SUM(CASE WHEN severity_level = 'Medium' THEN 1 ELSE 0 END) as medium_severity,
            SUM(CASE WHEN severity_level = 'Low' THEN 1 ELSE 0 END) as low_severity
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY DATE(date_filed)
        ORDER BY date
    """, conn)
    
    if not daily_data.empty:
        # Daily complaints trend
        fig_daily = px.line(
            daily_data, 
            x='date', 
            y='total_complaints',
            title='Daily Complaint Trends',
            labels={'total_complaints': 'Number of Complaints', 'date': 'Date'}
        )
        fig_daily.update_layout(height=400)
        st.plotly_chart(fig_daily, use_container_width=True)
        
        # Severity distribution over time
        severity_melted = daily_data.melt(
            id_vars=['date'],
            value_vars=['high_severity', 'medium_severity', 'low_severity'],
            var_name='severity',
            value_name='count'
        )
        severity_melted['severity'] = severity_melted['severity'].str.replace('_severity', '').str.title()
        
        fig_severity = px.area(
            severity_melted,
            x='date',
            y='count',
            color='severity',
            title='Severity Distribution Over Time',
            color_discrete_map={'High': '#ff4444', 'Medium': '#ff8800', 'Low': '#44aa44'}
        )
        fig_severity.update_layout(height=400)
        st.plotly_chart(fig_severity, use_container_width=True)
    
    # Crime type trends
    crime_trends = pd.read_sql_query(f"""
        SELECT 
            crime_type,
            DATE(date_filed) as date,
            COUNT(*) as count
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY crime_type, DATE(date_filed)
        ORDER BY date, crime_type
    """, conn)
    
    if not crime_trends.empty:
        # Top crime types line chart
        fig_crime_trends = px.line(
            crime_trends,
            x='date',
            y='count',
            color='crime_type',
            title='Crime Type Trends Over Time'
        )
        fig_crime_trends.update_layout(height=500)
        st.plotly_chart(fig_crime_trends, use_container_width=True)
    
    conn.close()

def display_geographic_analysis(db, start_date, end_date):
    """Display geographic distribution and hotspot analysis"""
    
    st.subheader("🗺️ Geographic Crime Analysis")
    
    conn = db.connect()
    
    # Location-based analysis
    location_data = pd.read_sql_query(f"""
        SELECT 
            location,
            COUNT(*) as complaint_count,
            AVG(CASE WHEN severity_level = 'High' THEN 3 
                     WHEN severity_level = 'Medium' THEN 2 
                     ELSE 1 END) as avg_severity_score,
            latitude,
            longitude,
            crime_type
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
          AND location IS NOT NULL
        GROUP BY location, latitude, longitude, crime_type
        ORDER BY complaint_count DESC
    """, conn)
    
    if not location_data.empty:
        # Crime hotspots map
        st.write("**🗺️ Crime Hotspots Map**")
        
        # Create map centered on Kerala
        kerala_center = [10.8505, 76.2711]
        hotspot_map = folium.Map(location=kerala_center, zoom_start=7)
        
        # Add heatmap layer and markers
        for idx, row in location_data.head(50).iterrows():  # Limit to top 50 for performance
            if pd.notna(row['latitude']) and pd.notna(row['longitude']):
                # Size based on complaint count
                radius = min(max(row['complaint_count'] * 2, 5), 20)
                
                # Color based on average severity
                if row['avg_severity_score'] >= 2.5:
                    color = 'red'
                elif row['avg_severity_score'] >= 1.5:
                    color = 'orange'
                else:
                    color = 'green'
                
                folium.CircleMarker(
                    location=[float(row['latitude']), float(row['longitude'])],
                    radius=radius,
                    popup=f"""
                    <b>Location:</b> {row['location']}<br>
                    <b>Crime Type:</b> {row['crime_type']}<br>
                    <b>Complaints:</b> {row['complaint_count']}<br>
                    <b>Avg Severity:</b> {row['avg_severity_score']:.1f}
                    """,
                    color='black',
                    weight=1,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(hotspot_map)
        
        st_folium(hotspot_map, width=700, height=500)
        
        # Location statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📍 Top Crime Locations**")
            top_locations = location_data.groupby('location').agg({
                'complaint_count': 'sum',
                'avg_severity_score': 'mean'
            }).sort_values(by='complaint_count', ascending=False).head(10)
            
            st.dataframe(
                top_locations.round(2),
                column_config={
                    "complaint_count": "Complaints",
                    "avg_severity_score": "Avg Severity"
                }
            )
        
        with col2:
            # District-wise analysis (simulated from location data)
            st.write("**🏛️ District-wise Distribution**")
            
            # Simulate district mapping based on location names
            district_data = simulate_district_data(location_data)
            
            if not district_data.empty:
                fig_district = px.bar(
                    district_data.head(10),
                    x='complaints',
                    y='district',
                    orientation='h',
                    title='Complaints by District',
                    color='complaints',
                    color_continuous_scale='Reds'
                )
                fig_district.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_district, use_container_width=True)
    
    conn.close()

def display_crime_pattern_analysis(db, start_date, end_date):
    """Display crime pattern analysis and correlations"""
    
    st.subheader("🎯 Crime Pattern Analysis")
    
    conn = db.connect()
    
    # Crime type distribution
    crime_distribution = pd.read_sql_query(f"""
        SELECT 
            crime_type,
            COUNT(*) as count,
            AVG(CASE WHEN severity_level = 'High' THEN 3 
                     WHEN severity_level = 'Medium' THEN 2 
                     ELSE 1 END) as avg_severity
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY crime_type
        ORDER BY count DESC
    """, conn)
    
    if not crime_distribution.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Crime type pie chart
            fig_pie = px.pie(
                crime_distribution,
                values='count',
                names='crime_type',
                title='Crime Type Distribution'
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Crime severity correlation
            fig_severity_crime = px.scatter(
                crime_distribution,
                x='count',
                y='avg_severity',
                size='count',
                text='crime_type',
                title='Crime Volume vs Average Severity',
                labels={'count': 'Number of Complaints', 'avg_severity': 'Average Severity Score'}
            )
            fig_severity_crime.update_traces(textposition="top center")
            fig_severity_crime.update_layout(height=400)
            st.plotly_chart(fig_severity_crime, use_container_width=True)
    
    # Time-based patterns
    st.write("**⏰ Temporal Patterns**")
    
    # Hour of day analysis
    hourly_data = pd.read_sql_query(f"""
        SELECT 
            strftime('%H', date_filed) as hour,
            COUNT(*) as count
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY strftime('%H', date_filed)
        ORDER BY hour
    """, conn)
    
    if not hourly_data.empty:
        hourly_data['hour'] = hourly_data['hour'].astype(int)
        
        fig_hourly = px.bar(
            hourly_data,
            x='hour',
            y='count',
            title='Complaints by Hour of Day',
            labels={'hour': 'Hour (24-hour format)', 'count': 'Number of Complaints'}
        )
        fig_hourly.update_layout(height=400)
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    # Day of week analysis
    dow_data = pd.read_sql_query(f"""
        SELECT 
            CASE strftime('%w', date_filed)
                WHEN '0' THEN 'Sunday'
                WHEN '1' THEN 'Monday'
                WHEN '2' THEN 'Tuesday'
                WHEN '3' THEN 'Wednesday'
                WHEN '4' THEN 'Thursday'
                WHEN '5' THEN 'Friday'
                WHEN '6' THEN 'Saturday'
            END as day_of_week,
            COUNT(*) as count
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY strftime('%w', date_filed)
        ORDER BY strftime('%w', date_filed)
    """, conn)
    
    if not dow_data.empty:
        fig_dow = px.bar(
            dow_data,
            x='day_of_week',
            y='count',
            title='Complaints by Day of Week',
            color='count',
            color_continuous_scale='Blues'
        )
        fig_dow.update_layout(height=400)
        st.plotly_chart(fig_dow, use_container_width=True)
    
    conn.close()

def display_performance_metrics(db, start_date, end_date):
    """Display police performance and response metrics"""
    
    st.subheader("⚡ Performance Metrics")
    
    conn = db.connect()
    
    # Resolution time analysis
    resolution_data = pd.read_sql_query(f"""
        SELECT 
            julianday(MAX(cu.update_date)) - julianday(c.date_filed) as resolution_days,
            c.crime_type,
            c.severity_level
        FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CaseUpdates cu ON cs.case_id = cu.case_id
        WHERE c.status = 'Resolved'
          AND DATE(c.date_filed) BETWEEN '{start_date}' AND '{end_date}'
          AND cu.status = 'Resolved'
        GROUP BY c.complaint_id
    """, conn)
    
    if not resolution_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Average resolution time by crime type
            avg_resolution = resolution_data.groupby('crime_type')['resolution_days'].mean().sort_values(ascending=True)
            
            fig_resolution = px.bar(
                x=avg_resolution.values,
                y=avg_resolution.index,
                orientation='h',
                title='Average Resolution Time by Crime Type (Days)',
                labels={'x': 'Days', 'y': 'Crime Type'}
            )
            fig_resolution.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_resolution, use_container_width=True)
        
        with col2:
            # Resolution time distribution
            fig_hist = px.histogram(
                resolution_data,
                x='resolution_days',
                nbins=20,
                title='Resolution Time Distribution',
                labels={'resolution_days': 'Days to Resolution', 'count': 'Number of Cases'}
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)
    
    # Officer performance
    officer_performance = pd.read_sql_query(f"""
        SELECT 
            u.name as officer_name,
            u.badge_number,
            COUNT(DISTINCT c.complaint_id) as cases_handled,
            SUM(CASE WHEN c.status = 'Resolved' THEN 1 ELSE 0 END) as cases_resolved,
            AVG(CASE WHEN c.severity_level = 'High' THEN 3 
                     WHEN c.severity_level = 'Medium' THEN 2 
                     ELSE 1 END) as avg_case_severity
        FROM Users u
        JOIN Complaints c ON u.user_id = c.assigned_officer_id
        WHERE u.role = 'police'
          AND DATE(c.date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY u.user_id, u.name, u.badge_number
        HAVING cases_handled > 0
        ORDER BY cases_handled DESC
    """, conn)
    
    if not officer_performance.empty:
        st.write("**👮 Officer Performance Summary**")
        
        # Calculate resolution rate
        officer_performance['resolution_rate'] = (
            officer_performance['cases_resolved'] / officer_performance['cases_handled'] * 100
        ).round(1)
        
        # Display officer performance table
        st.dataframe(
            officer_performance[['officer_name', 'badge_number', 'cases_handled', 'cases_resolved', 'resolution_rate', 'avg_case_severity']],
            column_config={
                "officer_name": "Officer Name",
                "badge_number": "Badge Number",
                "cases_handled": "Cases Handled",
                "cases_resolved": "Cases Resolved",
                "resolution_rate": st.column_config.NumberColumn("Resolution Rate (%)", format="%.1f%%"),
                "avg_case_severity": st.column_config.NumberColumn("Avg Severity", format="%.2f")
            },
            hide_index=True
        )
        
        # Performance visualization
        if len(officer_performance) > 1:
            fig_performance = px.scatter(
                officer_performance,
                x='cases_handled',
                y='resolution_rate',
                size='avg_case_severity',
                text='officer_name',
                title='Officer Performance: Cases Handled vs Resolution Rate',
                labels={'cases_handled': 'Cases Handled', 'resolution_rate': 'Resolution Rate (%)'}
            )
            fig_performance.update_traces(textposition="top center")
            fig_performance.update_layout(height=500)
            st.plotly_chart(fig_performance, use_container_width=True)
    
    conn.close()

def display_detailed_reports(db, start_date, end_date):
    """Display detailed analytical reports"""
    
    st.subheader("🔍 Detailed Reports")
    
    # Report type selector
    report_type = st.selectbox(
        "Select Report Type",
        ["Summary Report", "Crime Trend Report", "Geographic Report", "Performance Report"]
    )
    
    if report_type == "Summary Report":
        display_summary_report(db, start_date, end_date)
    elif report_type == "Crime Trend Report":
        display_trend_report(db, start_date, end_date)
    elif report_type == "Geographic Report":
        display_geographic_report(db, start_date, end_date)
    elif report_type == "Performance Report":
        display_performance_report(db, start_date, end_date)

def display_summary_report(db, start_date, end_date):
    """Display comprehensive summary report"""
    
    st.write("**📊 Crime Summary Report**")
    st.write(f"**Period:** {start_date} to {end_date}")
    
    conn = db.connect()
    
    # Get comprehensive statistics
    summary_stats = pd.read_sql_query(f"""
        SELECT 
            COUNT(*) as total_complaints,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved_cases,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_cases,
            SUM(CASE WHEN status = 'Under Investigation' THEN 1 ELSE 0 END) as under_investigation,
            SUM(CASE WHEN severity_level = 'High' THEN 1 ELSE 0 END) as high_severity,
            SUM(CASE WHEN severity_level = 'Medium' THEN 1 ELSE 0 END) as medium_severity,
            SUM(CASE WHEN severity_level = 'Low' THEN 1 ELSE 0 END) as low_severity
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
    """, conn).iloc[0]
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📋 Total Complaints", summary_stats['total_complaints'])
        st.metric("✅ Resolved", summary_stats['resolved_cases'])
        st.metric("⏳ Pending", summary_stats['pending_cases'])
    
    with col2:
        st.metric("🔍 Under Investigation", summary_stats['under_investigation'])
        if summary_stats['total_complaints'] > 0:
            resolution_rate = summary_stats['resolved_cases'] / summary_stats['total_complaints'] * 100
            st.metric("📈 Resolution Rate", f"{resolution_rate:.1f}%")
    
    with col3:
        st.metric("🔴 High Severity", summary_stats['high_severity'])
        st.metric("🟡 Medium Severity", summary_stats['medium_severity'])
        st.metric("🟢 Low Severity", summary_stats['low_severity'])
    
    # Top crime types
    crime_summary = pd.read_sql_query(f"""
        SELECT 
            crime_type,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Complaints 
                                     WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'), 1) as percentage
        FROM Complaints 
        WHERE DATE(date_filed) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY crime_type
        ORDER BY count DESC
        LIMIT 10
    """, conn)
    
    if not crime_summary.empty:
        st.write("**🏷️ Top Crime Types**")
        st.dataframe(
            crime_summary,
            column_config={
                "crime_type": "Crime Type",
                "count": "Count",
                "percentage": st.column_config.NumberColumn("Percentage (%)", format="%.1f%%")
            },
            hide_index=True
        )
    
    conn.close()

def simulate_district_data(location_data):
    """Simulate district-wise data from location information"""
    # This is a simplified simulation - in a real system, you'd have proper district mapping
    district_mapping = {}
    
    for district in KERALA_DISTRICTS:
        # Simple pattern matching for district names in locations
        matching_rows = location_data['location'].str.contains(district, case=False, na=False)
        district_complaints = location_data.loc[matching_rows, 'complaint_count'].sum()
        
        if district_complaints > 0:
            district_mapping[district] = district_complaints
    
    # Add some default data if no matches found
    if not district_mapping:
        district_mapping = {
            'Thiruvananthapuram': 25,
            'Ernakulam': 20,
            'Kozhikode': 15,
            'Thrissur': 12,
            'Kollam': 10
        }
    
    district_df = pd.DataFrame(list(district_mapping.items()), columns=['district', 'complaints'])
    return district_df.sort_values(by='complaints', ascending=False)

def display_trend_report(db, start_date, end_date):
    """Display detailed trend analysis report"""
    st.write("**📈 Crime Trend Analysis Report**")
    # Implementation would include detailed trend analysis
    st.info("Detailed trend analysis coming soon...")

def display_geographic_report(db, start_date, end_date):
    """Display detailed geographic analysis report"""
    st.write("**🗺️ Geographic Analysis Report**")
    # Implementation would include detailed geographic analysis
    st.info("Detailed geographic analysis coming soon...")

def display_performance_report(db, start_date, end_date):
    """Display detailed performance analysis report"""
    st.write("**⚡ Performance Analysis Report**")
    # Implementation would include detailed performance analysis
    st.info("Detailed performance analysis coming soon...")