from ursina import *
import random

app = Ursina()
window.title = "Race World - Texture Edition"

# Global Progression Stats
game_state = "PLAYING"
player_cash = 500
selected_track = "City Grid"
engine_level = 1
brake_level = 1
armor_level = 1

# --- SYSTEM ADDONS ---
particles = []

# Mapped clear transparent presets with unlit texture states
car_presets = {
    "1": {"name": "Toyota Supra Mk4", "scale": (3.5, 1.8, 1), "color": color.white, "max_speed": 45, "turn_speed": 65, "accel": 0.5, "texture": "supra.png"},
    "2": {"name": "Ford F-150 Raptor", "scale": (4.2, 2.8, 1), "color": color.white, "max_speed": 32, "turn_speed": 45, "accel": 0.3, "texture": "raptor.png"},
    "3": {"name": "Ferrari LaFerrari", "scale": (3.6, 1.6, 1), "color": color.white, "max_speed": 68, "turn_speed": 85, "accel": 0.8, "texture": "laferrari.png"}
}

# ----------------------------------------------------
# 3D ENVIRONMENT BLOCK GENERATOR
# ----------------------------------------------------
world_parent = Entity()
sky = Sky(parent=world_parent)
time_of_day = 0.0

# Base terrain plane layout setup
ground = Entity(model='plane', scale=(1000, 1, 1000), texture='grass.jpg', texture_scale=(200, 200), collider='mesh', parent=world_parent)
ground.color = color.white

# Roads Framework Layout
roads = []
for z in range(-300, 301, 150):
    roads.append(Entity(model='cube', scale=(600, 0.02, 12), texture='asphalt.jpg', texture_scale=(60, 1), color=color.white, position=(0, 0.01, z), parent=world_parent))
for x in range(-300, 301, 150):
    roads.append(Entity(model='cube', scale=(12, 0.02, 600), texture='asphalt.jpg', texture_scale=(1, 60), color=color.white, position=(x, 0.01, 0), parent=world_parent))

# SUBURBAN HOUSES SETUP (Optimized into 2D Billboard Quads)
houses = []
for i in range(35):
    hx, hz = random.randint(-200, 200), random.randint(-200, 200)
    if abs(hx) % 150 > 15 and abs(hz) % 150 > 15:
        # Changed to flat quad shapes with an unlit shader to completely hide background boxes
        house = Entity(
            model='quad', 
            texture='house_facade.png', 
            shader=unlit_textures_shader,
            color=color.white, 
            scale=(18, random.randint(11, 16), 1), 
            position=(hx, 6, hz), 
            collider='box', 
            parent=world_parent
        )
        houses.append(house)

# AI TRAFFIC GRID (Rebalanced for flat side-profile hatchback image asset)
traffic_cars = []
for i in range(12):
    traffic = Entity(
        model='quad', 
        texture='civilian_car.png', 
        shader=unlit_textures_shader,
        color=color.white, 
        scale=(5.5, 2.2, 1), 
        position=(random.randint(-150, 150), 1.1, random.choice([-150, 0, 150])), 
        collider='box', 
        parent=world_parent
    )
    traffic.rotation_y = random.choice([90, -90])
    traffic_cars.append(traffic)

# COP AI INTERCEPTOR
cop_car = Entity(model='quad', texture='cop_car.png', shader=unlit_textures_shader, color=color.white, scale=(4.0, 2.2, 1), position=(100, 1.1, 100), collider='box', parent=world_parent)
cop_siren = Entity(model='cube', color=color.blue, scale=(0.8, 0.15, 0.3), position=(0, 1.2, -0.1), parent=cop_car)
wanted_level = 0

race_active = False
race_timer = 0
race_checkpoint = Entity(model='cube', color=color.rgba(255, 255, 0, 100), scale=(15, 10, 2), position=(0, 5, 75), collider='box', parent=world_parent)

is_multiplayer = False
p1_damage = 0
p1_speed = 0
p1_max_speed = car_presets["1"]["max_speed"]
p1_turn_speed = car_presets["1"]["turn_speed"]
p1_accel = car_presets["1"]["accel"]

# PLAYER CAR INITIALIZATION (Shifted over to flat quad sprite architecture)
player1 = Entity(model='quad', texture=car_presets["1"]["texture"], shader=unlit_textures_shader, color=color.white, scale=car_presets["1"]["scale"], position=(0, 0.9, -10), collider='box', parent=world_parent)

hud_text = Text(text="", position=(-0.85, 0.45), scale=1.1, color=color.black)
race_hud = Text(text="", position=(-0.2, 0.4), scale=1.8, color=color.red, enabled=False)
cash_hud = Text(text="CASH: $500", position=(0.6, 0.45), scale=2, color=color.green)

mouse.locked = True

def trigger_crash_fx(position):
    for i in range(15):  
        p = Entity(model='cube', color=random.choice([color.orange, color.yellow, color.red]), scale=random.uniform(0.2, 0.6), position=position + Vec3(random.uniform(-1,1), random.uniform(0,1), random.uniform(-1,1)), parent=world_parent)
        p.velocity = Vec3(random.uniform(-10, 10), random.uniform(5, 15), random.uniform(-10, 10)); particles.append(p)

def input(key):
    global p1_max_speed, p1_turn_speed, p1_accel
    if key in car_presets:
        preset = car_presets[key]
        player1.scale = preset["scale"]
        player1.texture = preset["texture"] 
        player1.shader = unlit_textures_shader
        player1.color = color.white
        p1_max_speed = preset["max_speed"] + (engine_level - 1) * 8
        p1_turn_speed = preset["turn_speed"]
        p1_accel = preset["accel"]

def update():
    global p1_speed, race_active, race_timer, time_of_day, player_cash, p1_damage, wanted_level

    for p in particles[:]:
        p.position += p.velocity * time.dt; p.velocity.y -= 25 * time.dt; p.scale -= 1 * time.dt        
        if p.scale_x <= 0: particles.remove(p); destroy(p)

    time_of_day += 12 * time.dt
    if time_of_day > 360: time_of_day = 0
    if 160 < time_of_day < 340:
        sky.color = color.dark_gray
        ground.color = color.black
    else:
        sky.color = color.cyan
        ground.color = color.white

    damage_penalty = max(0.3, 1.0 - (p1_damage / 100.0)); current_p1_max = p1_max_speed * damage_penalty; current_p1_accel = p1_accel

    if held_keys['space'] and p1_speed > 10:
        current_p1_max *= 1.4; current_p1_accel *= 2.0; player1.color = color.yellow
    else:
        player1.color = color.white

    if held_keys['w']: p1_speed = min(p1_speed + current_p1_accel, current_p1_max)
    elif held_keys['s']: p1_speed = max(p1_speed - 0.8, -10)
    else: p1_speed = max(p1_speed - 0.2, 0) if p1_speed > 0 else min(p1_speed + 0.2, 0)

    if p1_speed != 0:
        p1_dir = 1 if p1_speed > 0 else -1
        if held_keys['a']: player1.rotation_y -= p1_turn_speed * time.dt * p1_dir
        if held_keys['d']: player1.rotation_y += p1_turn_speed * time.dt * p1_dir
    player1.position += player1.forward * p1_speed * time.dt

    if p1_speed > 45: wanted_level = 1
    if wanted_level > 0:
        cop_siren.color = color.blue if int(time_of_day) % 2 == 0 else color.red
        cop_car.look_at(player1.position)
        cop_car.rotation_x = 0; cop_car.rotation_z = 0 # Locks the cop vertical
        cop_car.position += cop_car.forward * 22 * time.dt
        if distance(cop_car.position, player1.position) < 4:
            p1_damage = min(100, p1_damage + max(2, 15 - (armor_level - 1) * 4)); p1_speed *= 0.4; cop_car.position -= cop_car.forward * 10; trigger_crash_fx(player1.position) 

    for traffic in traffic_cars:
        # Dynamically lock the traffic car angles so the side of the car faces parallel paths
        traffic.look_at(camera.position)
        traffic.rotation_x = 0; traffic.rotation_z = 0
        
        traffic.position += traffic.forward * 14 * time.dt
        if abs(traffic.x) > 300: traffic.x = -traffic.x
        if distance(player1.position, traffic.position) < 4:
            p1_damage = min(100, p1_damage + max(2, 20 - armor_level * 5)); p1_speed *= -0.3; traffic.position += player1.forward * 15; trigger_crash_fx(player1.position) 
        if distance(player1.position, traffic.position) < 7 and p1_speed > 25:
            player_cash += 2; cash_hud.text = f"CASH: ${player_cash}"

    # DYNAMIC BILLBOARD HOUSE HANDLER
    for house in houses:
        house.look_at(camera.position) # Forces the flat building to turn face-forward toward your car
        house.rotation_x = 0
        house.rotation_z = 0
        if distance(player1.position, house.position) < 10:
            p1_damage = min(100, p1_damage + max(2, 25 - armor_level * 6)); p1_speed = -5; trigger_crash_fx(player1.position) 

    if distance(player1.position, race_checkpoint.position) < 15 and not race_active:
        race_active = True; race_timer = 20.0; race_hud.enable(); race_checkpoint.position = (random.choice([-120, 0, 120]), 5, random.choice([-120, 0, 120]))
    if race_active:
        race_timer -= time.dt; race_hud.text = f"RACE RUN RUNNING: {race_timer:.1f}s"
        if distance(player1.position, race_checkpoint.position) < 12:
            race_active = False; player_cash += 600; wanted_level = 0; race_hud.text = "RACE WON! ESCAPED COPS +$600"; cash_hud.text = f"CASH: ${player_cash}"; race_checkpoint.position = (0, 5, 75)
        if race_timer <= 0: race_active = False; race_hud.text = "TIME EXPIRED! MISSION OUT."; race_checkpoint.position = (0, 5, 75)

    # Core Driving Camera Tracking System
    camera.position = player1.position + player1.up * 6 - player1.forward * 15; camera.look_at(player1.position + player1.up * 1.5)

    hud_text.text = f"SPEED: {int(p1_speed)} MPH\nDAMAGE: {int(p1_damage)}%\nPOLICE STATUS: {'PURSUIT ACTIVE' if wanted_level > 0 else 'CLEAR'}\n\nVEHICLE CONTROLS:\n[1] Toyota Supra\n[2] Ford Raptor\n[3] LaFerrari\n[SPACE] Nitro Boost"

app.run()
