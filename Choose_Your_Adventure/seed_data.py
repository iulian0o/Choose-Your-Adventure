import requests

BASE_URL = "http://localhost:5000"

# Story 1: The Enchanted Forest
story1 = requests.post(f"{BASE_URL}/stories", json={
    "title": "The Enchanted Forest",
    "description": "A magical adventure in a mysterious forest",
    "status": "published"
}).json()

print(f"Created story: {story1['title']} (ID: {story1['id']})")

# Create pages
page1 = requests.post(f"{BASE_URL}/stories/{story1['id']}/pages", json={
    "text": "You stand at the edge of an enchanted forest. Two paths lie before you.",
    "is_ending": False
}).json()

page2 = requests.post(f"{BASE_URL}/stories/{story1['id']}/pages", json={
    "text": "You discover hidden treasure and befriend forest spirits!",
    "is_ending": True,
    "ending_label": "Treasure Hunter"
}).json()

page3 = requests.post(f"{BASE_URL}/stories/{story1['id']}/pages", json={
    "text": "You become a guardian of the forest with magical powers!",
    "is_ending": True,
    "ending_label": "Forest Guardian"
}).json()

# Create choices
requests.post(f"{BASE_URL}/pages/{page1['id']}/choices", json={
    "text": "Enter the dark woods",
    "next_page_id": page2['id']
})

requests.post(f"{BASE_URL}/pages/{page1['id']}/choices", json={
    "text": "Follow the sparkling stream",
    "next_page_id": page3['id']
})

print("✓ Story 1 complete with 2 endings")

# Story 2: Space Station Crisis
story2 = requests.post(f"{BASE_URL}/stories", json={
    "title": "Space Station Crisis",
    "description": "Save the station from disaster",
    "status": "published"
}).json()

p1 = requests.post(f"{BASE_URL}/stories/{story2['id']}/pages", json={
    "text": "Alarms blare! The oxygen system is failing. You must act quickly.",
    "is_ending": False
}).json()

p2 = requests.post(f"{BASE_URL}/stories/{story2['id']}/pages", json={
    "text": "You fix the system just in time. The crew is saved!",
    "is_ending": True,
    "ending_label": "Hero"
}).json()

p3 = requests.post(f"{BASE_URL}/stories/{story2['id']}/pages", json={
    "text": "The evacuation is successful, but the station is lost.",
    "is_ending": True,
    "ending_label": "Survivor"
}).json()

requests.post(f"{BASE_URL}/pages/{p1['id']}/choices", json={
    "text": "Repair the oxygen generator",
    "next_page_id": p2['id']
})

requests.post(f"{BASE_URL}/pages/{p1['id']}/choices", json={
    "text": "Evacuate everyone to escape pods",
    "next_page_id": p3['id']
})

print("✓ Story 2 complete")
print("\n=== All test data created! ===")