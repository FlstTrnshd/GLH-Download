from flask import render_template, request, redirect, url_for, flash
from SQLAlch_setup import app, db, User
from flask_login import LoginManager, login_user, current_user, AnonymousUserMixin, logout_user
import json
import os

login_manager = LoginManager()


#Edits the default Anonymous User so they can access the rest of the site
class MyAnonymousUser(AnonymousUserMixin):
    def __init__(self):
        self.name = "Anon"
        self.AccType = "Guest"

login_manager.init_app(app)
login_manager.anonymous_user = MyAnonymousUser

data_dir = os.path.join(os.path.dirname(__file__), "Data")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

app.secret_key = 'secret_k3y'

#checks if the user is logged in and sends them to the appropriate page
@app.route("/")
def load_check():
    if current_user.is_authenticated:
        return redirect(url_for('main_page'))
    else:
        return redirect(url_for('LogIn'))

#Main Page
@app.route("/main")
def main_page():
    return render_template("Main_HTML.html", status=current_user.AccType, signedIn=current_user.is_authenticated)

#When the user submits the login form, this checks the credentials against users.db
@app.route("/login_process", methods=["POST"])
def login_process():
    username = request.form.get("username")
    password = request.form.get("password")

    user = db.session.execute(db.select(User).filter_by(name=username, pw=password)).scalar_one_or_none()

    if user:
        login_user(user)

        return redirect(url_for('main_page'))
    else:
        return "Invalid Credentials", 401

#when the Register form is submitted, this checks the credentials against users.db and adds a user if no username/id conflicts are found
@app.route("/register_process", methods=["GET", "POST"])
def register_process():
    username = request.form.get("username")
    password = request.form.get("password")
    confpassword = request.form.get("confpassword")
    acctype = "User"

    existing_user = db.session.execute(
        db.select(User).filter_by(name=username)
    ).scalar_one_or_none()
    
    if existing_user:
        return redirect(url_for("register"))

    if password != confpassword:
        return redirect(url_for("register"))
    
    new_user = User(name=username, pw=password, AccType=acctype)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("LogIn"))

@app.route("/market")
def market():
    try:
        with open(os.path.join(data_dir, "listings.json"), "r") as f:
            all_products = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_products = []

    return render_template("Market_HTML.html", status=current_user.AccType, signedIn=current_user.is_authenticated, products=all_products)


@app.route("/add_to_basket", methods=["POST"])
def add_to_basket():
    if not current_user.is_authenticated or not current_user.name:
        return redirect(url_for('LogIn'))

    item_id = request.form.get("item_id")

    try:
        with open(os.path.join(data_dir, "listings.json"), "r") as f:
            listings = json.load(f)
        with open(os.path.join(data_dir, "basket.json"), "r") as f:
            all_baskets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "Error: Data files not found", 500

    target_item = next((item for item in listings if item.get("id") == item_id), None)

    if target_item and int(target_item.get("units", 0)) > 0:
        target_item["units"] = int(target_item["units"]) - 1

        if current_user.name not in all_baskets:
            all_baskets[current_user.name] = []
        all_baskets[current_user.name].append(item_id)

        with open(os.path.join(data_dir, "listings.json"), "w") as f:
            json.dump(listings, f, indent=4)
        with open(os.path.join(data_dir, "basket.json"), "w") as f:
            json.dump(all_baskets, f, indent=4)
        return redirect(url_for('market'))
    return "Item out of stock or not found", 400

@app.route("/basket")
def basket():
    if not current_user.is_authenticated:
        return redirect(url_for('LogIn'))

    try:
        with open(os.path.join(data_dir, "basket.json"), "r") as f:
            all_baskets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_baskets = {}

    user_basket = all_baskets.get(current_user.name, [])

    # Count quantities
    quantities = {}
    for item_id in user_basket:
        quantities[item_id] = quantities.get(item_id, 0) + 1

    try:
        with open(os.path.join(data_dir, "listings.json"), "r") as f:
            listings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        listings = []

    # Create dict of id to item
    items_dict = {item['id']: item for item in listings}

    basket_items = []
    total = 0.0
    for item_id, qty in quantities.items():
        item = items_dict.get(item_id)
        if item:
            price = float(item['unit-price'])
            subtotal = qty * price
            total += subtotal
            basket_items.append({
                'id': item_id,
                'name': item['name'],
                'desc': item['desc'],
                'price': price,
                'qty': qty,
                'subtotal': subtotal
            })

    return render_template("Basket.html", basket_items=basket_items, total=total, status=current_user.AccType, signedIn=current_user.is_authenticated)

@app.route("/about")
def about():
    return render_template("About_HTML.html", status = current_user.AccType, signedIn = current_user.is_authenticated)

@app.route("/AddProd", methods=["GET", "POST"])
def AddProd():
    return render_template("AddProd.html", status = current_user.AccType, signedIn = current_user.is_authenticated, currentUser = current_user.name)

@app.route("/add_prod_process", methods=["POST"])
def add_prod_process():
    new_entry = {
        "name": request.form.get("name"),
        "lister": current_user.name,
        "desc": request.form.get("desc"),
        "units": request.form.get("units"),
        "unit-price": request.form.get("unit-price")
    }

    file_path = os.path.join(data_dir, "listings.json")
    try:
        with open(file_path, "r") as f:
            listings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        listings = []

    if not listings:
        next_id = "Prod-01"
    else:
        existing_ids = []
        for item in listings:
            if "id" in item:
                num_part = int(item["id"].split('-')[1])
                existing_ids.append(num_part)
        
        next_num = max(existing_ids) + 1 if existing_ids else 1
        next_id = f"Prod-{next_num:02d}"

    new_entry["id"] = next_id
    listings.append(new_entry)

    with open(file_path, "w") as f:
        json.dump(listings, f, indent=4)

    return redirect(url_for('market'))

@app.route("/EditProd/<prod_id>")
def EditProd(prod_id):
    prod_name = prod_units = prod_price = prod_desc = None
    file_path = os.path.join(data_dir, "listings.json")
    
    try:
        with open(file_path, "r") as f:
            listings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        listings = []

    for item in listings:
        if item.get("id") == prod_id:
            prod_name = item.get("name")
            prod_units = item.get("units")
            prod_price = item.get("unit-price")
            prod_desc = item.get("desc")
            break
            
    return render_template("EditProd.html", product=prod_id, prod_name=prod_name, prod_units=prod_units, prod_price=prod_price, prod_desc=prod_desc)

@app.route("/delete_prod/<prod_id>", methods=["POST", "GET"])
def delete_prod(prod_id):
    file_path = os.path.join(data_dir, "listings.json")
    
    try:
        with open(file_path, "r") as f:
            listings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "File not found", 404

    # Keep everything EXCEPT the item with the matching ID
    new_listings = [item for item in listings if item.get("id") != prod_id]

    with open(file_path, "w") as f:
        json.dump(new_listings, f, indent=4)

    return redirect(url_for("EditProdList"))

@app.route("/edit_list_process/<id>", methods=["POST", "GET"])
def edit_list_process(id):
    edit_entry = {
        "id": id,
        "name": request.form.get("name"),
        "lister": current_user.name,
        "desc": request.form.get("desc"),
        "units": request.form.get("units"),
        "unit-price": request.form.get("unit-price")
    }
    
    file_path = os.path.join(data_dir, "listings.json")
    
    try:
        with open(file_path, "r") as f:
            listings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "File not found", 404

    found = False
    for index, item in enumerate(listings):
        if item.get("id") == id:
            listings[index] = edit_entry
            found = True
            break
            
    if not found:
        return "Product ID not found", 404

    with open(file_path, "w") as f:
        json.dump(listings, f, indent=4)

    return redirect(url_for("EditProdList"))

@app.route("/EditProdList")
def EditProdList():
    current_user_clean = str(current_user.name).strip()
    
    prodlist = []
    file_path = os.path.join(data_dir, "listings.json")
    
    try:
        with open(file_path, "r") as f:
            listings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        listings = []
    
    for product in listings:
        lister_in_json = str(product.get("lister", "")).strip()
        if lister_in_json == current_user_clean:
            prodlist.append(product)
            
    return render_template("EditProdList.html", products=prodlist, status=current_user.AccType, signedIn=current_user.is_authenticated,)

@app.route("/AdminPanel")
def AdminPanel():
    if not current_user.is_authenticated or current_user.AccType != "Administrator":
        return "Access Denied", 403

    all_users = db.session.execute(db.select(User)).scalars().all()

    file_path = os.path.join(data_dir, "listings.json")
    try:
        with open(file_path, "r") as f:
            all_prods = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_prods = []

    role_options = ["User", "Producer", "Administrator"]

    return render_template("AdminPanel.html", 
                           users=all_users, 
                           products=all_prods, 
                           roles=role_options,
                           status=current_user.AccType, 
                           signedIn=current_user.is_authenticated)

@app.route("/update_user_role/<int:user_id>", methods=["POST"])
def update_user_role(user_id):
    if not current_user.is_authenticated or current_user.AccType != "Administrator":
        return "Unauthorized", 403

    new_role = request.form.get("new_role")
    
    user_to_update = db.session.get(User, user_id)
    
    if user_to_update:
        user_to_update.AccType = new_role
        db.session.commit()
        flash(f"Updated {user_to_update.name} to {new_role}")
    
    return redirect(url_for('AdminPanel'))

@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    if not current_user.is_authenticated or current_user.AccType != "Administrator":
        return "Unauthorized", 403

    user_to_delete = db.session.get(User, user_id)
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User deleted successfully")
        
    return redirect(url_for('AdminPanel'))


@app.route("/LogIn")
def LogIn():
    return render_template("LogIn.html")

@app.route("/SignOut")
def SignOut():
    logout_user()
    return redirect(url_for("LogIn"))

@app.route("/register")
def register():
    return render_template("Register.html")

if __name__ == "__main__":
    app.run(debug=True)