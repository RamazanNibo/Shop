import asyncio
import os
from utils import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import sqlite3
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
data = sqlite3.connect("../shop.db")
cur = data.cursor()


# Start the bot
# 启动机器人
async def main():
    print("Бот работает!")
    await dp.start_polling(bot)


# States for adding a product
# 添加商品时使用的状态
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    count = State()
    img = State()


# States for editing a product
# 编辑商品时使用的状态
class EditProduct(StatesGroup):
    name = State()
    edit = State()
    edit_text = State()


# States for working with the cart
# 购物车操作时使用的状态
class CartProduct(StatesGroup):
    name = State()
    count = State()


# States for buying a product
# 购买商品时使用的状态
class BuyProduct(StatesGroup):
    name = State()
    count = State()
    confirm = State()

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Состояние сброшено")


# Create database tables and show the main menu
# 创建数据库表并显示主菜单
@dp.message(Command("start"))
async def cmd_start(message: Message):
    create_tables(data)
    clear_empty(data)
    data.commit()
    print("старт")
    text = ("Добро пожаловать в наш магазин!\n\n"
            "Доступные команды:\n\n"
            "/list — список товаров\n"
            "/buy — купить товар\n"
            "/cart — добавить товар в корзину\n"
            "/cart_list — посмотреть корзину\n"
            "/cart_buy — оформить покупку из корзины\n"
            "/orders — мои заказы\n\n"
            "Для начала работы выберите нужную команду.")
    if check_admin(message, cur):
        text += ("\n\nКоманды администратора:\n\n"
                 "/add — добавить товар\n"
                 "/update — изменить товар\n"
                 "/all_orders — просмотр всех заказов")
    await message.answer(text)


# Start adding a product
# 开始添加商品
@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    if check_admin(message, cur):
        await message.answer("Введите название товара")
        await state.set_state(AddProduct.name)
    else:
        await message.answer("У вас нет прав администратора")


# Save the product name
# 保存商品名称
@dp.message(AddProduct.name)
async def add_name(message: Message, state: FSMContext):
    if check_name(message, cur):
        await message.answer("Товар с таким названием уже есть, введите другое")
    else:
        await state.update_data(name=message.text)
        await message.answer("Введите описание товара")
        await state.set_state(AddProduct.description)


# Save the product description
# 保存商品描述
@dp.message(AddProduct.description)
async def add_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Введите цену товара в рублях")
    await state.set_state(AddProduct.price)


# Save the product price
# 保存商品价格
@dp.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext):
    price = check_number(message.text)
    if price is None:
        await message.answer("Цена должна быть числом больше нуля")
        return
    await state.update_data(price=price)
    await message.answer("Введите количество товара")
    await state.set_state(AddProduct.count)


# Save the product quantity
# 保存商品数量
@dp.message(AddProduct.count)
async def add_count(message: Message, state: FSMContext):
    count = check_number(message.text)
    if count is None:
        await message.answer("Количество должно быть числом больше нуля")
        return
    await state.update_data(count=count)
    await message.answer("Введите сыллку на изображение")
    await state.set_state(AddProduct.img)


# Save the image and add the product to the database
# 保存图片并将商品添加到数据库
@dp.message(AddProduct.img)
async def add_count(message: Message, state: FSMContext):
    await state.update_data(img=message.text)
    product = await state.get_data()
    data.execute("insert into shop (name,description,price,count,img) values (?,?,?,?,?)", list(product.values()))
    data.commit()
    await state.clear()
    await message.answer("Продукт добавлен:\n"
                         f"Название:{product["name"]}\n"
                         f"Описание:{product["desc"]}\n"
                         f"Цена:{product["price"]}\n"
                         f"Количество:{product["count"]}\n"
                         f"Изображение:{product["img"]}\n")


# Start editing a product
# 开始编辑商品
@dp.message(Command("update"))
async def cmd_add(message: Message, state: FSMContext):
    if check_admin(message, cur):
        await message.answer("Введите название продукта")
        await state.set_state(EditProduct.name)
    else:
        await message.answer("У вас нет прав администратора")


# Save the product name for editing
# 保存需要编辑的商品名称
@dp.message(EditProduct.name)
async def edit_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Что вы хотите поменять name,description,price,count,img ")
    await state.set_state(EditProduct.edit)


# Select the field to edit
# 选择需要修改的字段
@dp.message(EditProduct.edit)
async def edit(message: Message, state: FSMContext):
    if message.text in ["name", "description", "price", "count", "img"]:
        await state.update_data(edit=message.text)
        await message.answer("Введите новое значение")
        await state.set_state(EditProduct.edit_text)
    else:
        await message.answer("Выберите 1 из вариантов из предложенного списка")


# Update the selected product field
# 更新选中的商品字段
@dp.message(EditProduct.edit_text)
async def edit_text(message: Message, state: FSMContext):
    await state.update_data(edit_text=message.text)
    product = await state.get_data()
    if product["edit"] in ["price","count"] and check_number(message.text) is None:
        await message.answer("Это значение должно быть больше нуля")
        return
    cur.execute(f"""update shop set {product["edit"]} = '{product["edit_text"]}' where name = '{product["name"]}'""")
    clear_empty(data)
    data.commit()
    await message.answer("Данные изменены")
    await state.clear()


# Show the product list
# 显示商品列表
@dp.message(Command("list"))
async def cmd_list(message: Message):
    await message.answer(f"Список товаров:\n\n{get_products_text(cur)}")


# Start buying a product
# 开始购买商品
@dp.message(Command("buy"))
async def cmd_buy(message: Message, state: FSMContext):
    text = get_products_text(cur)
    if text:
        await message.answer(f"Введите название продукта\n\nСписок товаров:\n\n{text}")
        await state.set_state(BuyProduct.name)
    else:
        await message.answer("Товаров нет")


# Check the selected product
# 检查选择的商品
@dp.message(BuyProduct.name)
async def buy_name(message: Message, state: FSMContext):
    name = message.text
    cur.execute("select id, count from shop where name = ?", (name,))
    buy = cur.fetchone()
    if buy != None:
        await state.update_data(name=name)
        await message.answer(f"Товара в наличии: {buy[1]}.Введите количество:")
        await state.set_state(BuyProduct.count)
    else:
        await message.answer("Такого товара нет.")


# Check the quantity and calculate the total price
# 检查数量并计算总价格
@dp.message(BuyProduct.count)
async def Buy_count(message: Message, state: FSMContext):
    user = message.from_user.id
    try:
        count = int(message.text)
        if count <= 0:
            await message.answer("Количество должно быть больше нуля")
            return
        await state.update_data(count=message.text)
        buy = await state.get_data()
        cur.execute(f"""select price,count from shop where name = '{buy["name"]}'""")
        price = cur.fetchone()
        tot_price = int(price[0]) * int(buy["count"])
        if int(buy["count"]) <= 0:
            await message.answer("Количество должно быть больше нуля.")
            return
        if int(buy["count"]) > price[1]:
            await message.answer(f"Доступно только {price[1]} шт.")
            return
        await message.answer(
            f"Товар: {buy['name']}\n"
            f"Количество: {buy["count"]}\n"
            f"Цена за штуку: {price[0]}\n"
            f"Общая цена: {tot_price}\n\n"
            f"Подтвердить покупку? Напишите да или нет."
        )
        await state.set_state(BuyProduct.confirm)
    except:
        await message.answer("Количество должно быть цифровым значением")
        return


# Confirm the purchase and update the stock
# 确认购买并更新库存
@dp.message(BuyProduct.confirm)
async def buy_confirm(message: Message, state: FSMContext):
    answer = message.text.lower()
    if answer == "да":
        user = message.from_user.id
        buy = await state.get_data()
        price, tot_price = make_order(user, buy["name"], buy["count"], data, cur)
        await state.clear()
        await message.answer(
            f"Покупка подтверждена.\n"
            f"Название: {buy['name']}\n"
            f"Количество: {buy['count']}\n"
            f"Цена за штуку: {price}\n"
            f"Общая цена: {tot_price}"
        )
        clear_empty(data)
        data.commit()
    else:
        await state.clear()
        await message.answer("Покупка отменена")


# Start adding a product to the cart
# 开始将商品加入购物车
@dp.message(Command("cart"))
async def cmd_add_to_cart(message: Message, state: FSMContext):
    if get_products_text(cur) is not None:
        await message.answer(f"Введите название продукта\n\nСписок товаров:\n\n{get_products_text(cur)}")
        await state.set_state(CartProduct.name)
    else:
        await message.answer("Товаров нет")


# Check the selected product for the cart
# 检查购物车中选择的商品
@dp.message(CartProduct.name)
async def cart_name(message: Message, state: FSMContext):
    name = message.text
    user = message.from_user.id
    cur.execute("select id, count from shop where name = ?", (name,))
    cart = cur.fetchone()
    cur.execute("select count from cart where name = ? and user = ?", (name,user ))
    x = cur.fetchall()
    if cart != None:
        curcount = cart[1] - sum(i[0] for i in x)
        await state.update_data(name=name)
        await message.answer(f"Товара в наличии: {curcount}.Введите количество:")
        await state.set_state(CartProduct.count)
    else:
        await message.answer("Такого товара нет.")


# Add the selected product to the cart
# 将选择的商品加入购物车
@dp.message(CartProduct.count)
async def Cart_count(message: Message, state: FSMContext):
    user = message.from_user.id
    try:
        mes = int(message.text)
    except:
        await message.answer("Введите количество числом.")
        return
    if mes <= 0:
        await message.answer("Количество должно быть больше нуля.")
        return
    await state.update_data(count=mes)
    acart = await state.get_data()
    cur.execute("select price,count,img from shop where name = ?", (acart["name"],))
    cart = cur.fetchone()
    print(cart)
    cur.execute("select count from cart where name = ? and user = ?", (acart["name"], user))
    x = cur.fetchall()
    sum_count = sum(i[0] for i in x) + int(mes)
    print(sum(i[0] for i in x))
    if cart is None:
        await message.answer("Такого товара нет.")
        return
    if sum_count <= cart[1]:
        price = acart["count"] * cart[0]
        data.execute("insert into cart (user,name,count,price,image) values (?,?,?,?,?)",
                     [user, acart["name"], acart["count"], price,cart[2]])
        data.commit()
        await state.clear()
        await message.answer(
            f"Товар добавлен в корзину.\n"
            f"Название: {acart["name"]}\n"
            f"Количество: {acart["count"]}\n"
            f"Стоимость: {price}"
        )
    else:
        await message.answer(
            f"Доступно только {cart[1]} шт."
        )


# Show the user's orders
# 显示用户的订单
@dp.message(Command("orders"))
async def cmd_list(message: Message):
    user = message.from_user.id
    cur.execute(f"select date,name,tot_price,count from orders where user = {user}")
    orders = cur.fetchall()
    text = "Ваши заказы:\n\n"
    for date, name, total_price, count in orders:
        text += (
            f"Дата: {date}\n"
            f"Название: {name}\n"
            f"Количество: {count}\n"
            f"Сумма: {total_price}\n\n"
        )
    await message.answer(text)


# Show all orders for the administrator
# 显示管理员的所有订单
@dp.message(Command("all_orders"))
async def cmd_list(message: Message):
    if check_admin(message, cur):
        cur.execute("select user,date,name,tot_price,count from orders")
        orders = cur.fetchall()
        text = "Все заказы:\n\n"
        for user, date, name, total_price, count in orders:
            userinfo = await bot.get_chat(user)
            text += (
                f"Пользователь: {userinfo.username}\n"
                f"Дата: {date}\n"
                f"Название: {name}\n"
                f"Количество: {count}\n"
                f"Сумма: {total_price}\n\n"
            )
        await message.answer(text)
    else:
        await message.answer("У вас нет прав администратора")


# Add the current user to the admin table
# 将当前用户添加到管理员表
@dp.message(Command("admin5987"))
async def cmd_list(message: Message):
    user_id = message.from_user.id
    cur.execute(f"select user_id from admin where user_id = {user_id}")
    usid = cur.fetchone()
    if usid is None:
        cur.execute("insert into admin (user_id) values (?)", (user_id,))
        data.commit()
        await message.answer("Права администратора получены")
    else:
        await message.answer("Вы уже являетесь администратором")


# Show the current user's cart
# 显示当前用户的购物车
@dp.message(Command("cart_list"))
async def cmd_clist(message: Message):
    user = message.from_user.id
    cur.execute(f"select name,count,price,image from cart where user = {user}")
    cart = cur.fetchall()
    tot_price = 0
    text = "Ваша корзина:\n\n"
    for name, count, price,image in cart:
        tot_price += price
        text += f"Название: {name}\nКоличество: {count}\nЦена: {price}\n{image}\n"
    await message.answer(f"{text}\nИтого:{tot_price}")


@dp.message(Command("cart_clear"))
async def cart_clear(message: Message, state: FSMContext):
    user_id = message.from_user.id
    cur.execute(f"delete from cart where user = {user_id}")
    await message.answer("Корзина очищена")


# Buy all products from the cart
# 购买购物车中的所有商品
@dp.message(Command("cart_buy"))
async def cmd_cbuy(message: Message):
    user = message.from_user.id
    cur.execute("select name, count, price from cart where user = ?", (user,))
    cart_items = cur.fetchall()
    if not cart_items:
        await message.answer("Ваша корзина пуста.")
        return

    # Sum the quantity of the same products in the cart
    # 合并购物车中相同商品的数量
    cart_count = {}
    for name, count, price in cart_items:
        cart_count[name] = cart_count.get(name, 0) + count

    # Check the stock before buying
    # 购买前检查库存
    for name, count in cart_count.items():
        cur.execute("select count from shop where name = ?", (name,))
        product = cur.fetchone()
        if product is None:
            await message.answer(f"Товара {name} больше нет в магазине.")
            return
        if count > product[0]:
            await message.answer(
                f"Товара {name} доступно только {product[0]} шт, а в корзине {count} шт."
            )
            return

    total_price = 0
    for name, count, price in cart_items:
        shop_price, item_price = make_order(user, name, count, data, cur)
        total_price += item_price
    clear_empty(data)
    data.commit()
    await message.answer(
        f"Покупка корзины подтверждена!\n\n"
        f"Товаров: {len(cart_items)}\n"
        f"Общая стоимость: {total_price}"
    )


# Run the bot
# 运行机器人
asyncio.run(main())
