import random
import hashlib
from faker import Faker
from datetime import datetime, timedelta
from database import Database

db = Database()
db.init_db()  # Ensure tables are created

# Clear existing data
print("🗑️ Clearing existing data...")
try:
    # Delete in proper order to handle foreign key constraints
    db.cursor.execute("DELETE FROM complaint_updates")
    db.cursor.execute("DELETE FROM complaints") 
    db.cursor.execute("DELETE FROM users")
    db.connection.commit()
    print("✅ Existing data cleared successfully.\n")
except Exception as e:
    print(f"⚠️ Warning: Could not clear existing data: {e}\n")

fake = Faker('en_IN')

# --- Enhanced Setup with More Realistic Data ---

kerala_locations = [
    "Thiruvananthapuram", "Kochi", "Kollam", "Alappuzha", "Thrissur", "Palakkad",
    "Kozhikode", "Kannur", "Ernakulam", "Kottayam", "Pathanamthitta", "Wayanad",
    "Idukki", "Malappuram", "Kasargod", "Chavakkad", "Ponnani", "Thodupuzha",
    "Perumbavoor", "Aluva", "Kayamkulam", "Changanassery", "Kothamangalam"
]

# Accurate coordinates for Kerala locations (verified Indian coordinates)
city_coords = {
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kochi": (9.9312, 76.2673),
    "Kollam": (8.8932, 76.6141),
    "Alappuzha": (9.4981, 76.3388),
    "Thrissur": (10.5276, 76.2144),
    "Palakkad": (10.7867, 76.6548),
    "Kozhikode": (11.2588, 75.7804),
    "Kannur": (11.8745, 75.3704),
    "Ernakulam": (9.9816, 76.2999),
    "Kottayam": (9.5916, 76.5222),
    "Pathanamthitta": (9.2642, 76.7870),
    "Wayanad": (11.6854, 76.1320),
    "Idukki": (9.8492, 77.0663),
    "Malappuram": (11.0519, 76.0711),
    "Kasargod": (12.4996, 74.9866),
    "Chavakkad": (10.5908, 76.0158),
    "Ponnani": (10.7667, 75.9255),
    "Thodupuzha": (9.8894, 76.7194),
    "Perumbavoor": (10.1102, 76.4733),
    "Aluva": (10.1081, 76.3528),
    "Kayamkulam": (9.1747, 76.5019),
    "Changanassery": (9.4459, 76.5436),
    "Kothamangalam": (10.0581, 76.6350)
}

# More realistic crime types based on Indian context
crime_types = [
    "Theft", "House Breaking", "Chain Snatching", "Mobile Phone Theft", 
    "Vehicle Theft", "Fraud", "Cyber Crime", "Domestic Violence",
    "Assault", "Eve Teasing", "Dowry Harassment", "Land Dispute",
    "Cheating", "Criminal Intimidation", "Rioting", "Drug Possession",
    "Drunk Driving", "Traffic Violation", "Forgery", "Bribery"
]

# Realistic complaint descriptions based on crime types
crime_descriptions = {
    "Theft": [
        "My purse was stolen from the bus while travelling from {} to {}",
        "Cash worth ₹{} was stolen from my shop during night hours",
        "Jewelry worth ₹{} lakhs was stolen from my residence while we were away"
    ],
    "House Breaking": [
        "Unknown persons broke into my house and stole valuables worth ₹{} lakhs",
        "Burglars entered through the back door and took electronic items",
        "My house was broken into during daytime and gold ornaments were stolen"
    ],
    "Chain Snatching": [
        "Two persons on a motorcycle snatched my gold chain worth ₹{} lakhs",
        "While walking near {} market, unknown person snatched my chain and fled",
        "Chain snatching incident occurred near {} bus stand in broad daylight"
    ],
    "Vehicle Theft": [
        "My motorcycle (KL-{}-{}) was stolen from {} parking area",
        "Four-wheeler (KL-{}-{}) was stolen from near my residence",
        "Auto-rickshaw was stolen while parked outside {} temple"
    ],
    "Cyber Crime": [
        "Fraudulent transaction of ₹{} from my bank account through unknown app",
        "Someone created fake profile using my photos and demanding money",
        "Received fake call claiming lottery win and lost ₹{} to fraudsters"
    ],
    "Domestic Violence": [
        "Physical assault by husband demanding additional dowry",
        "Harassment by in-laws for not bringing sufficient dowry amount",
        "Husband threatening to divorce if more money not given"
    ],
    "Fraud": [
        "Lost ₹{} lakhs in fake investment scheme promising high returns",
        "Cheated by person who took advance for property sale but disappeared",
        "Online shopping fraud - paid ₹{} but goods never delivered"
    ]
}

severities = ["Low", "Medium", "High"]
statuses = ["Pending", "Under Investigation", "Resolved", "Closed"]

# Police departments in Kerala
police_departments = [
    "Crime Branch", "Traffic Police", "Cyber Cell", "Women Cell",
    "Narcotic Cell", "Economic Offences", "Law and Order", "Special Branch"
]

# --- Helper ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_realistic_description(crime_type, location):
    """Generate realistic crime descriptions based on type and location"""
    if crime_type in crime_descriptions:
        template = random.choice(crime_descriptions[crime_type])
        
        # Count placeholders in template
        placeholder_count = template.count('{}')
        
        if placeholder_count > 0:
            if crime_type == "Chain Snatching":
                if placeholder_count == 1:
                    return template.format(location)
                else:
                    return template.format(random.randint(50000, 300000) // 100000, location)
            elif crime_type == "Theft":
                if "from {} to {}" in template:
                    nearby_location = random.choice(kerala_locations)
                    return template.format(location, nearby_location)
                else:
                    return template.format(random.randint(10000, 500000))
            elif crime_type == "House Breaking":
                return template.format(random.randint(50000, 500000) // 100000)
            elif crime_type == "Vehicle Theft":
                if placeholder_count == 1:
                    return template.format(location)
                elif placeholder_count == 2:
                    district_code = random.randint(1, 99)
                    vehicle_num = random.randint(1000, 9999)
                    return template.format(f"{district_code:02d}", f"{vehicle_num}")
                else:
                    district_code = random.randint(1, 99)
                    vehicle_num = random.randint(1000, 9999)
                    return template.format(f"{district_code:02d}", f"{vehicle_num}", location)
            elif crime_type == "Cyber Crime":
                return template.format(random.randint(5000, 100000))
            elif crime_type == "Fraud":
                if "₹{} lakhs" in template:
                    return template.format(random.randint(1, 20))
                else:
                    return template.format(random.randint(5000, 50000))
            else:
                return template.format(location)
        else:
            return template
    else:
        return f"Incident related to {crime_type.lower()} occurred at {location}. " + fake.text(max_nb_chars=150)

def add_coordinate_variation(lat, lon):
    """Add small random variation to coordinates to simulate exact incident locations"""
    # Add variation within ~2km radius (approximately 0.02 degrees)
    lat_variation = random.uniform(-0.02, 0.02)
    lon_variation = random.uniform(-0.02, 0.02)
    return round(lat + lat_variation, 6), round(lon + lon_variation, 6)

# --- Create Users ---

print("🔐 Creating Users...")

# Create 5 Police Officers with different departments
police_credentials = []
officer_ids = []

for i in range(5):
    police_email = f"officer{i+1}@keralapolice.in"
    police_password = f"officer12{i+1}"
    police_hashed = hash_password(police_password)
    
    officer_id = db.create_user(
        name=f"Inspector {fake.first_name()} {fake.last_name()}",
        email=police_email,
        phone=fake.phone_number(),
        password_hash=police_hashed,
        role="police",
        district=random.choice(kerala_locations),
        badge_number=f"KP{1001+i}",
        department=random.choice(police_departments)
    )
    
    police_credentials.append({
        'email': police_email,
        'password': police_password,
        'badge': f"KP{1001+i}"
    })
    officer_ids.append(officer_id)

# Create 15 Citizens with Indian names
citizen_credentials = []
citizen_password = "citizen123"
citizen_hashed = hash_password(citizen_password)
citizen_ids = []

indian_names = [
    "Rajesh Kumar", "Priya Sharma", "Amit Singh", "Sunita Devi", "Vikash Gupta",
    "Anita Kumari", "Suresh Nair", "Meera Menon", "Ravi Pillai", "Kavitha Nair",
    "Arun Kumar", "Lakshmi Devi", "Mahesh Varma", "Sowmya Raj", "Deepak Krishnan"
]

for i, name in enumerate(indian_names):
    email = f"citizen{i+1}@gmail.com"
    user_id = db.create_user(
        name=name,
        email=email,
        phone=f"+91-{random.randint(7000000000, 9999999999)}",
        password_hash=citizen_hashed,
        role="citizen",
        district=random.choice(kerala_locations)
    )
    citizen_credentials.append({
        'email': email,
        'password': citizen_password,
        'name': name
    })
    citizen_ids.append(user_id)

print(f"✅ Created {len(officer_ids)} Police Officers and {len(citizen_ids)} Citizens.\n")

# --- Create Realistic Complaints ---
print("📂 Inserting realistic complaints...")

for _ in range(100):  # Increased to 100 complaints
    citizen_id = random.choice(citizen_ids)
    citizen = db.get_user_by_id(citizen_id)

    if citizen is None:
        continue

    crime_type = random.choice(crime_types)
    
    # Realistic severity distribution
    if crime_type in ["Chain Snatching", "House Breaking", "Vehicle Theft", "Domestic Violence"]:
        severity = random.choices(severities, weights=[0.2, 0.5, 0.3])[0]
    elif crime_type in ["Cyber Crime", "Fraud"]:
        severity = random.choices(severities, weights=[0.3, 0.6, 0.1])[0]
    else:
        severity = random.choices(severities, weights=[0.5, 0.3, 0.2])[0]
    
    location = random.choice(kerala_locations)
    description = generate_realistic_description(crime_type, location)
    status = random.choices(statuses, weights=[0.4, 0.35, 0.2, 0.05])[0]

    # More recent incidents (last 60 days)
    days_ago = random.randint(0, 60)
    incident_date = datetime.now() - timedelta(days=days_ago)

    severity_score = {
        "Low": round(random.uniform(1.0, 3.5), 1),
        "Medium": round(random.uniform(3.6, 7.0), 1),
        "High": round(random.uniform(7.1, 10.0), 1)
    }[severity]

    # Get coordinates and add variation
    base_lat, base_lon = city_coords.get(location, (None, None))
    if base_lat is None or base_lon is None:
        continue

    latitude, longitude = add_coordinate_variation(base_lat, base_lon)

    ref_number = db.submit_complaint({
        'citizen_name': citizen['name'],
        'citizen_email': citizen['email'],
        'citizen_phone': citizen['phone'],
        'crime_type': crime_type,
        'description': description,
        'location': location,
        'latitude': latitude,
        'longitude': longitude,
        'incident_date': incident_date.strftime('%Y-%m-%d'),
        'severity_level': severity,
        'severity_score': float(severity_score)
    })

    # Assign officer and update status if not 'Pending'
    if status != "Pending" and officer_ids:
        complaint = db.get_complaint_by_reference(ref_number)
        if complaint:
            assigned_officer = random.choice(police_credentials)
            db.update_complaint_status(
                complaint_id=complaint['complaint_id'],
                new_status=status,
                officer_badge=assigned_officer['badge'],
                notes=f"Case {status.lower()} after investigation. " + 
                      ("Evidence collected and action taken." if status == "Resolved" 
                       else "Investigation ongoing." if status == "Under Investigation" 
                       else "Case closed due to insufficient evidence.")
            )

print("✅ Inserted 100 realistic complaints with Indian context.")

# --- Print Credentials ---
print("\n" + "="*60)
print("🧾 LOGIN CREDENTIALS")
print("="*60)

print("\n👮 POLICE OFFICERS:")
print("-" * 40)
for i, cred in enumerate(police_credentials):
    print(f"{i+1}. Email: {cred['email']}")
    print(f"   Password: {cred['password']}")
    print(f"   Badge: {cred['badge']}\n")

print("🧑 CITIZENS:")
print("-" * 40)
for i, cred in enumerate(citizen_credentials[:10]):  # Show first 10
    print(f"{i+1}. Email: {cred['email']} | Password: {cred['password']} | Name: {cred['name']}")

if len(citizen_credentials) > 10:
    print(f"... and {len(citizen_credentials) - 10} more citizens with password: {citizen_password}")

print("\n" + "="*60)
print("✅ Database seeded successfully with realistic Indian data!")
print("📍 All coordinates are within Kerala, India")
print(f"📊 Total: {len(police_credentials)} officers, {len(citizen_credentials)} citizens, 100 complaints")
print("="*60)