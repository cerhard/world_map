import folium
import json
import os
from folium.features import CustomIcon
from PIL import Image, ImageDraw
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import pickle

# Load family data
with open('family.json', 'r') as f:
    family = json.load(f)

# Geocoding cache file
GEOCODE_CACHE_FILE = 'geocode_cache.pkl'
if os.path.exists(GEOCODE_CACHE_FILE):
    with open(GEOCODE_CACHE_FILE, 'rb') as f:
        geocode_cache = pickle.load(f)
else:
    geocode_cache = {}

# Geocoder setup
geolocator = Nominatim(user_agent="family_map")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def get_latlon(place_name):
    if place_name in geocode_cache:
        return geocode_cache[place_name]
    location = geocode(place_name)
    if location:
        latlon = (location.latitude, location.longitude)
        geocode_cache[place_name] = latlon
        with open(GEOCODE_CACHE_FILE, 'wb') as f:
            pickle.dump(geocode_cache, f)
        return latlon
    else:
        raise ValueError(f"Could not geocode location: {place_name}")

# Create map centered at a reasonable default
m = folium.Map(
    location=[20, 0],
    zoom_start=2,
    tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attr='&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

# Ensure images directory exists
os.makedirs('images', exist_ok=True)
# Directory for processed icons
os.makedirs('images/pins', exist_ok=True)
# Ensure www directory exists
os.makedirs('www', exist_ok=True)

def create_placeholder_image(path, name):
    img = Image.new('RGB', (30, 30), color=(200, 200, 200))
    d = ImageDraw.Draw(img)
    initials = ''.join([part[0] for part in name.split()]).upper()
    d.text((7, 10), initials, fill=(0, 0, 0))
    img.save(path)

def make_circular_icon(img_path, name):
    out_path = f"images/pins/{os.path.splitext(os.path.basename(img_path))[0]}_pin.png"
    size = (30, 30)
    border_colors = {
        'Carl': (0, 200, 0),    # Green
        'Julia': (200, 0, 0)    # Red
    }
    border_color = border_colors.get(name, (0, 0, 0))
    if not os.path.exists(img_path):
        create_placeholder_image(img_path, name)
    im = Image.open(img_path).convert('RGBA').resize(size)
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    circular = Image.new('RGBA', size)
    circular.paste(im, (0, 0), mask=mask)
    border_width = 2
    border = Image.new('RGBA', size)
    border_draw = ImageDraw.Draw(border)
    border_draw.ellipse((0, 0, size[0]-1, size[1]-1), outline=border_color, width=border_width)
    final = Image.alpha_composite(circular, border)
    final.save(out_path)
    return out_path

# Create a FeatureGroup for each family member
feature_groups = {}
for member in family:
    fg = folium.FeatureGroup(name=member['name'])
    feature_groups[member['name']] = fg
    img_path = member['image']
    pin_path = make_circular_icon(img_path, member['name'])
    for place in member['places']:
        # Determine coordinates
        if 'lat' in place and 'lon' in place:
            lat, lon = place['lat'], place['lon']
        else:
            lat, lon = get_latlon(place['name'])
        icon = CustomIcon(pin_path, icon_size=(30, 30))
        # URL is optional
        if 'url' in place and place['url']:
            html = f'<a href="{place["url"]}" target="_blank"><img src="{pin_path}" width="30" height="30"><br>{member["name"]} in {place["name"]}</a>'
        else:
            html = f'<img src="{pin_path}" width="30" height="30"><br>{member["name"]} in {place["name"]}'
        folium.Marker(
            location=[lat, lon],
            icon=icon,
            popup=folium.Popup(html, max_width=200)
        ).add_to(fg)
    fg.add_to(m)

# Add layer control to toggle family members
folium.LayerControl(collapsed=False).add_to(m)

m.save('www/output_map.html')
print('Map saved to www/output_map.html') 