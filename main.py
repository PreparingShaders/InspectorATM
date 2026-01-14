from handlers import admin_router, group_router, admin_storage

# В функции main():
dp = Dispatcher(storage=admin_storage)  # добавь sorage для FSM