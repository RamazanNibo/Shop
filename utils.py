# Check whether the user has administrator privileges.
# 检查用户是否具有管理员权限。
def check_admin(message, cur):
    user_id = message.from_user.id
    cur.execute("select user_id from admin where user_id = ?", [user_id, ])
    id = cur.fetchone()
    if id is not None:
        return True
    else:
        return False


# Create the database tables if they do not already exist.
# 如果数据库表不存在，则创建相应的数据表。
def create_tables(data):
    data.execute(
        "create table if not exists shop (id integer primary key autoincrement, name text unique, description text, img text, price integer, count integer)")
    data.execute(
        "create table if not exists orders (id integer primary key autoincrement, user text, date text, name text, tot_price integer, count integer)")
    data.execute(
        "create table if not exists cart (id integer primary key autoincrement, user text, name text, count integer, price integer, image str)")
    data.execute("create table if not exists admin (id integer primary key autoincrement, user_id integer unique)")
    data.commit()


# Check whether a product with the specified name already exists.
# 检查指定名称的商品是否已经存在。
def check_name(message, cur):
    cur.execute("select id from shop where name = ?", (message.text,))
    return True if cur.fetchone() is not None else False


# Create an order and decrease the available stock.
# 创建订单并减少可用库存。
def make_order(user, name, count, data, cur):
    cur.execute("select price from shop where name = ?", (name,))
    price = cur.fetchone()[0]
    tot_price = int(price) * int(count)
    data.execute("insert into orders (user,date,name,tot_price,count) values (?,datetime('now','localtime'),?,?,?)",
                 [user, name, tot_price, count])
    data.execute("update shop set count = count - ? where name = ?", (count, name))
    return price, tot_price


# Retrieve product information and format it as a text list.
# 获取商品信息并将其整理为文本列表。
def get_products_text(cur):
    cur.execute("select name,description,price,count,img from shop")
    text = ""
    for name, description, price, count, img in cur.fetchall():
        text += (
            f"Название: {name}\n"
            f"Описание: {description}\n"
            f"Цена: {price}\n"
            f"Количество: {count}\n"
            f"Изображение: {img}\n\n"
        )
    return text


# Convert text to an integer and check that it is at least 1.
# 将文本转换为整数，并检查其是否至少为 1。
def check_number(text):
    try:
        number = int(text)
    except:
        return None
    return number if number >= 1 else None


# Delete products with no remaining stock and remove their cart entries.
# 删除库存为零的商品，并移除购物车中的相关记录。
def clear_empty(data):
    data.execute("delete from shop where count <= 0")
    data.execute("delete from cart where not exists (select 1 from shop where shop.name = cart.name)")