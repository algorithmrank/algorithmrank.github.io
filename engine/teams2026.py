# 2026 FBS alignment (138 teams). Names follow the v6/CFBD spellings where the team existed in v6.
CONF_ORDER = ['ACC', 'American', 'Big 12', 'Big Ten', 'CUSA', 'Independent', 'MAC',
              'Mountain West', 'Pac-12', 'SEC', 'Sun Belt']

SHEET_FOR = {'ACC': 'ACC', 'American': 'American', 'Big 12': 'Big 12', 'Big Ten': 'Big Ten',
             'CUSA': 'CUSA', 'Independent': 'Independent', 'MAC': 'MAC',
             'Mountain West': 'Mountain West', 'Pac-12': 'Pac 12', 'SEC': 'SEC', 'Sun Belt': 'Sun Belt'}

CONFS = {
    'ACC': ['Boston College', 'California', 'Clemson', 'Duke', 'Florida State', 'Georgia Tech',
            'Louisville', 'Miami', 'NC State', 'North Carolina', 'Pittsburgh', 'SMU', 'Stanford',
            'Syracuse', 'Virginia', 'Virginia Tech', 'Wake Forest'],
    'American': ['Army', 'Charlotte', 'East Carolina', 'Florida Atlantic', 'Memphis', 'Navy',
                 'North Texas', 'Rice', 'South Florida', 'Temple', 'Tulane', 'Tulsa', 'UAB',
                 'UTSA'],
    'Big 12': ['Arizona', 'Arizona State', 'Baylor', 'BYU', 'Cincinnati', 'Colorado', 'Houston',
               'Iowa State', 'Kansas', 'Kansas State', 'Oklahoma State', 'TCU', 'Texas Tech', 'UCF',
               'Utah', 'West Virginia'],
    'Big Ten': ['Illinois', 'Indiana', 'Iowa', 'Maryland', 'Michigan', 'Michigan State', 'Minnesota',
                'Nebraska', 'Northwestern', 'Ohio State', 'Oregon', 'Penn State', 'Purdue', 'Rutgers',
                'UCLA', 'USC', 'Washington', 'Wisconsin'],
    'CUSA': ['Delaware', 'Florida International', 'Jacksonville State', 'Kennesaw State', 'Liberty',
             'Middle Tennessee', 'Missouri State', 'New Mexico State', 'Sam Houston',
             'Western Kentucky'],
    'Independent': ['Notre Dame', 'UConn'],
    'MAC': ['Akron', 'Ball State', 'Bowling Green', 'Buffalo', 'Central Michigan', 'Eastern Michigan',
            'Kent State', 'Miami (OH)', 'Ohio', 'Sacramento State', 'Toledo', 'Massachusetts',
            'Western Michigan'],
    # San José State is the only 13-game team in 2026 (Hawaii exemption) -> last slot, 13-row block
    'Mountain West': ['Air Force', "Hawai'i", 'Nevada', 'New Mexico', 'North Dakota State',
                      'Northern Illinois', 'UNLV', 'UTEP', 'Wyoming', 'San José State'],
    'Pac-12': ['Boise State', 'Colorado State', 'Fresno State', 'Oregon State', 'San Diego State',
               'Texas State', 'Utah State', 'Washington State'],
    'SEC': ['Alabama', 'Arkansas', 'Auburn', 'Florida', 'Georgia', 'Kentucky', 'LSU',
            'Mississippi State', 'Missouri', 'Oklahoma', 'Ole Miss', 'South Carolina', 'Tennessee',
            'Texas', 'Texas A&M', 'Vanderbilt'],
    'Sun Belt': ['App State', 'Arkansas State', 'Coastal Carolina', 'Georgia Southern',
                 'Georgia State', 'James Madison', 'Louisiana', 'UL Monroe', 'Louisiana Tech',
                 'Marshall', 'Old Dominion', 'South Alabama', 'Southern Miss', 'Troy'],
}

MASCOT = {
 'Boston College': 'Eagles', 'Clemson': 'Tigers', 'Duke': 'Blue Devils', 'Florida State': 'Seminoles',
 'Georgia Tech': 'Yellow Jackets', 'Louisville': 'Cardinals', 'Miami': 'Hurricanes', 'NC State': 'Wolfpack',
 'North Carolina': 'Tar Heels', 'Pittsburgh': 'Panthers', 'Syracuse': 'Orange', 'Virginia': 'Cavaliers',
 'Virginia Tech': 'Hokies', 'Wake Forest': 'Demon Deacons', 'California': 'Golden Bears',
 'Stanford': 'Cardinal', 'SMU': 'Mustangs', 'Charlotte': '49ers', 'East Carolina': 'Pirates',
 'Florida Atlantic': 'Owls', 'Memphis': 'Tigers', 'Navy': 'Midshipmen', 'Army': 'Black Knights',
 'South Florida': 'Bulls', 'Temple': 'Owls', 'Tulane': 'Green Wave', 'Tulsa': 'Golden Hurricane',
 'North Texas': 'Mean Green', 'Rice': 'Owls', 'UAB': 'Blazers', 'UTSA': 'Roadrunners',
 'Baylor': 'Bears', 'Iowa State': 'Cyclones', 'Kansas': 'Jayhawks', 'Kansas State': 'Wildcats',
 'Arizona': 'Wildcats', 'Oklahoma State': 'Cowboys', 'TCU': 'Horned Frogs', 'Arizona State': 'Sun Devils',
 'Texas Tech': 'Red Raiders', 'West Virginia': 'Mountaineers', 'Cincinnati': 'Bearcats',
 'Houston': 'Cougars', 'UCF': 'Knights', 'BYU': 'Cougars', 'Utah': 'Utes', 'Colorado': 'Buffaloes',
 'Illinois': 'Fighting Illini', 'Indiana': 'Hoosiers', 'Iowa': 'Hawkeyes', 'Maryland': 'Terrapins',
 'Michigan': 'Wolverines', 'Michigan State': 'Spartans', 'Minnesota': 'Golden Gophers',
 'Nebraska': 'Cornhuskers', 'Northwestern': 'Wildcats', 'Ohio State': 'Buckeyes',
 'Penn State': 'Nittany Lions', 'Purdue': 'Boilermakers', 'Rutgers': 'Scarlet Knights',
 'Wisconsin': 'Badgers', 'Oregon': 'Ducks', 'UCLA': 'Bruins', 'USC': 'Trojans', 'Washington': 'Huskies',
 'Jacksonville State': 'Gamecocks', 'Liberty': 'Flames', 'Florida International': 'Panthers',
 'Louisiana Tech': 'Bulldogs', 'Middle Tennessee': 'Blue Raiders', 'New Mexico State': 'Aggies',
 'Sam Houston': 'Bearkats', 'UTEP': 'Miners', 'Western Kentucky': 'Hilltoppers',
 'Kennesaw State': 'Owls', 'Notre Dame': 'Fighting Irish', 'UConn': 'Huskies', 'Massachusetts': 'Minutemen',
 'Akron': 'Zips', 'Ball State': 'Cardinals', 'Bowling Green': 'Falcons', 'Buffalo': 'Bulls',
 'Central Michigan': 'Chippewas', 'Eastern Michigan': 'Eagles', 'Kent State': 'Golden Flashes',
 'Miami (OH)': 'RedHawks', 'Northern Illinois': 'Huskies', 'Ohio': 'Bobcats', 'Toledo': 'Rockets',
 'Western Michigan': 'Broncos', 'Air Force': 'Falcons', 'Boise State': 'Broncos', 'Colorado State': 'Rams',
 'Fresno State': 'Bulldogs', "Hawai'i": 'Rainbow Warriors', 'Nevada': 'Wolf Pack', 'New Mexico': 'Lobos',
 'San Diego State': 'Aztecs', 'San José State': 'Spartans', 'UNLV': 'Rebels', 'Utah State': 'Aggies',
 'Wyoming': 'Cowboys', 'Oregon State': 'Beavers', 'Washington State': 'Cougars', 'Alabama': 'Crimson Tide',
 'Arkansas': 'Razorbacks', 'Auburn': 'Tigers', 'Florida': 'Gators', 'Georgia': 'Bulldogs',
 'Kentucky': 'Wildcats', 'LSU': 'Tigers', 'Mississippi State': 'Bulldogs', 'Missouri': 'Tigers',
 'Ole Miss': 'Rebels', 'South Carolina': 'Gamecocks', 'Tennessee': 'Volunteers', 'Texas A&M': 'Aggies',
 'Vanderbilt': 'Commodores', 'Texas': 'Longhorns', 'Oklahoma': 'Sooners',
 'App State': 'Mountaineers', 'Arkansas State': 'Red Wolves', 'Coastal Carolina': 'Chanticleers',
 'Georgia Southern': 'Eagles', 'Georgia State': 'Panthers', 'James Madison': 'Dukes',
 'Louisiana': "Ragin' Cajuns", 'Marshall': 'Thundering Herd', 'Old Dominion': 'Monarchs',
 'South Alabama': 'Jaguars', 'Southern Miss': 'Golden Eagles', 'Texas State': 'Bobcats',
 'Troy': 'Trojans', 'UL Monroe': 'Warhawks',
 # new FBS / new to this sheet
 'Delaware': 'Blue Hens', 'Missouri State': 'Bears', 'North Dakota State': 'Bison',
 'Sacramento State': 'Hornets',
}

# ESPN initial 2026 SP+ projections (Bill Connelly, Mar 27 2026), all 138 teams, rank order.
SP_PLUS = ['Ohio State', 'Oregon', 'Notre Dame', 'Georgia', 'Indiana', 'Texas', 'Texas Tech', 'Miami',
 'Texas A&M', 'LSU', 'Alabama', 'Oklahoma', 'USC', 'Michigan', 'Tennessee', 'Ole Miss', 'Penn State', 'BYU',
 'Florida', 'Missouri', 'Washington', 'Iowa', 'Clemson', 'South Carolina', 'Utah', 'Auburn', 'Louisville',
 'SMU', 'Kansas State', 'Arizona', 'Vanderbilt', 'Virginia Tech', 'Illinois', 'TCU', 'Florida State',
 'Houston', 'Nebraska', 'Oklahoma State', 'Boise State', 'Virginia', 'Pittsburgh', 'Arizona State',
 'Georgia Tech', 'Duke', 'Minnesota', 'UCLA', 'Arkansas', 'NC State', 'Northwestern', 'Cincinnati', 'Baylor',
 'Mississippi State', 'Kentucky', 'North Carolina', 'Maryland', 'California', 'Kansas', 'Wake Forest', 'UNLV',
 'UCF', 'Wisconsin', 'Rutgers', 'Navy', 'Iowa State', 'Colorado', 'West Virginia', 'Michigan State',
 'New Mexico', 'Syracuse', 'Memphis', 'San Diego State', 'North Dakota State', 'UTSA',
 'Boston College', 'Stanford', 'East Carolina', 'James Madison', 'Fresno State', 'Air Force', 'South Florida',
 'Miami (OH)', 'Purdue', 'Army', "Hawai'i", 'Washington State', 'Western Kentucky', 'Tulane', 'Old Dominion',
 'Texas State', 'Troy', 'Oregon State', 'Marshall', 'Liberty', 'Florida Atlantic', 'Western Michigan', 'Tulsa',
 'Utah State', 'Jacksonville State', 'Colorado State', 'Louisiana Tech', 'Arkansas State', 'Temple',
 'Georgia Southern', 'Louisiana', 'Kennesaw State', 'Wyoming', 'UConn', 'Toledo', 'North Texas',
 'Buffalo', 'App State', 'Nevada', 'Central Michigan', 'Delaware', 'Bowling Green', 'South Alabama',
 'Ohio', 'Florida International', 'Coastal Carolina', 'Rice', 'Eastern Michigan', 'San José State',
 'New Mexico State', 'UAB', 'Northern Illinois', 'Missouri State', 'Akron', 'Kent State', 'UTEP',
 'Sacramento State', 'Southern Miss', 'UL Monroe', 'Georgia State', 'Ball State',
 'Middle Tennessee', 'Sam Houston', 'Massachusetts', 'Charlotte']

# one block per team (unused capacity removed in v7.2)
CAPACITY = {SHEET_FOR[c]: len(CONFS[c]) for c in CONF_ORDER}
THIRTEEN = {'Mountain West': 10}   # sheet -> slot with a 13-game block

all_teams = [t for c in CONF_ORDER for t in CONFS[c]]
assert len(all_teams) == 138 and len(set(all_teams)) == 138, len(all_teams)
assert set(SP_PLUS) == set(all_teams), (set(SP_PLUS) ^ set(all_teams))
assert len(SP_PLUS) == 138
assert all(t in MASCOT for t in all_teams)
for c in CONF_ORDER:
    assert len(CONFS[c]) <= CAPACITY[SHEET_FOR[c]]
