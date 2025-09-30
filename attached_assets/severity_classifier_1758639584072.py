def classify_severity(title, description, category):
    """
    Classify complaint severity based on keywords and category
    Returns: 'low', 'medium', or 'high'
    """
    
    # Convert to lowercase for keyword matching
    text = f"{title} {description}".lower()
    
    # High severity keywords
    high_keywords = [
        'murder', 'kill', 'death', 'rape', 'assault', 'kidnap', 'bomb', 'terror',
        'weapon', 'gun', 'knife', 'violence', 'threat', 'emergency', 'urgent',
        'serious', 'critical', 'dangerous', 'life', 'injury', 'blood', 'attack'
    ]
    
    # Medium severity keywords
    medium_keywords = [
        'theft', 'robbery', 'fraud', 'cheat', 'scam', 'harassment', 'abuse',
        'domestic', 'cybercrime', 'blackmail', 'extortion', 'vandalism',
        'property', 'damage', 'stolen', 'missing', 'lost'
    ]
    
    # Low severity keywords
    low_keywords = [
        'noise', 'parking', 'dispute', 'argument', 'complaint', 'minor',
        'disturbance', 'nuisance', 'public', 'traffic', 'document'
    ]
    
    # Category-based severity
    high_severity_categories = ['murder', 'rape', 'kidnapping', 'terrorism', 'assault']
    medium_severity_categories = ['theft', 'fraud', 'cybercrime', 'harassment', 'robbery']
    low_severity_categories = ['traffic', 'noise', 'public nuisance', 'document']
    
    # Check category first
    if category.lower() in high_severity_categories:
        return 'high'
    elif category.lower() in medium_severity_categories:
        return 'medium'
    elif category.lower() in low_severity_categories:
        return 'low'
    
    # Check keywords
    high_count = sum(1 for keyword in high_keywords if keyword in text)
    medium_count = sum(1 for keyword in medium_keywords if keyword in text)
    low_count = sum(1 for keyword in low_keywords if keyword in text)
    
    # Determine severity based on keyword matches
    if high_count > 0:
        return 'high'
    elif medium_count > 0:
        return 'medium'
    elif low_count > 0:
        return 'low'
    else:
        # Default to medium if no keywords match
        return 'medium'

def get_severity_color(severity):
    """Get color code for severity level"""
    colors = {
        'high': '#ff4444',    # Red
        'medium': '#ff8800',  # Orange
        'low': '#44aa44'      # Green
    }
    return colors.get(severity, '#666666')

def get_severity_badge(severity):
    """Get HTML badge for severity"""
    color = get_severity_color(severity)
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
    ">
        {severity}
    </span>
    """
