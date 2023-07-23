import importlib

router_module_names = [
    "start_router",
    "subscription_router",
    "channel_request",
]


# функція, яка перезавантажує модулі та повертає нові роутери. Потрібно це, тому що не можна одні й ті самі
# об'єкти роутерів приєднувати до різних диспетчерів.
def get_routers():
    for module in router_module_names:
        importlib.reload(importlib.import_module("routers.ClientsBotRouters."+module))
    routers_answer = []
    for module in router_module_names:
        routers_answer.append(importlib.import_module(f"routers.ClientsBotRouters.{module}").router)
    return routers_answer
