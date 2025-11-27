from db import SessionLocal, init_db
from models import Group, Service, GroupService

def seed_initial_data(session):
    groups = {
        'Chipotle': {
            'name': 'Chipotle Flips',
            'webhook_footer': 'Chipotle Flips | Developed by bennybags#0344',
            'color': 'FF0000',
            'webhook_footer_img': 'https://cdn.discordapp.com/attachments/544093190865682432/1441714423839592508/ca_chefs_pig_logo.png?ex=6922ccb0&is=69217b30&hm=fc86c77c4075dd1822714dc2088b7153348019163c65ce0037029fe6b8a3dd04&',
            'webhook': 'https://discord.com/api/webhooks/1421719021321064469/0Knf40NtZHwysRPUIWRfreuypRiA88dERqqlHnDz6c9tYDZ4MrAKT34BYG3gEulGYVHQ',
        },
        'Chipotle2': {
            'name': 'Chipotle2',
            'webhook_footer': 'Chipotle2 | Developed by bennybags#0344',
            'color': 'FF0000',
            'webhook_footer_img': 'https://cdn.discordapp.com/attachments/544093190865682432/1441714423839592508/ca_chefs_pig_logo.png?ex=6922ccb0&is=69217b30&hm=fc86c77c4075dd1822714dc2088b7153348019163c65ce0037029fe6b8a3dd04&',
            'webhook': 'https://discord.com/api/webhooks/1421724635837501461/aqvgR00wv3ixxyQtmhIFKVPSbl9GzFTTRduL6wWSCA2z3U6CzqpSG_ZzSEdETimC-dxD',
        }
    }

    init_db()
    session = SessionLocal()

    for name, data in groups.items():
        existing = session.query(Group).filter(Group.name == name).first()
        if existing:
            print(f"Skipping existing group: {name}")
            continue
        group = Group(
            name=data['name'],
            webhook_footer=data['webhook_footer'],
            color=data['color'],
            webhook_footer_img=data['webhook_footer_img'],
            webhook_url=data['webhook'],
            enabled=True,
        )
        session.add(group)

    service1 = Service(name='Fooji')
    service2 = Service(name='Food Promos')
    session.add_all([service1, service2])
    session.commit()

    groups_db = session.query(Group).all()
    services_db = session.query(Service).all()

    # Example: Chipotle Flips has Service 1 enabled, Service 2 disabled
    gs1 = GroupService(group_id=groups_db[0].id, service_id=services_db[0].id, enabled=True)
    gs2 = GroupService(group_id=groups_db[0].id, service_id=services_db[1].id, enabled=False)

    # Example: Chipotle2 has Service 1 enabled only
    gs3 = GroupService(group_id=groups_db[1].id, service_id=services_db[0].id, enabled=True)

    session.add_all([gs1, gs2, gs3])
    session.commit()

    print("Seeded groups, services, and group-service links.")

if __name__ == "__main__":
    init_db()
    sess = SessionLocal()
    seed_initial_data(sess)
    sess.close()