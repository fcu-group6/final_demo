from django.shortcuts import render, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout

from datetime import datetime
import math
from .models import *
from capstone.utils import render_to_pdf, createticket
from django.contrib.auth.decorators import login_required


#Fee and Surcharge variable
from .constant import FEE
from flight.utils import createWeekDays, addPlaces, addDomesticFlights, addInternationalFlights

import requests
from django.conf import settings

from django.shortcuts import render, redirect
from .forms import AddressForm

from django.shortcuts import get_object_or_404, redirect
from .models import Address

import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render

from django.http import JsonResponse

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import Messages
from django.http import JsonResponse
import json
from django.shortcuts import render
from googleapiclient.discovery import build 

try:
    if len(Week.objects.all()) == 0:
        createWeekDays()

    if len(Place.objects.all()) == 0:
        addPlaces()

    if len(Flight.objects.all()) == 0:
        print("Do you want to add flights in the Database? (y/n)")
        if input().lower() in ['y', 'yes']:
            addDomesticFlights()
            addInternationalFlights()
except:
    pass

# Create your views here.

def index(request):
    min_date = f"{datetime.now().date().year}-{datetime.now().date().month}-{datetime.now().date().day}"
    max_date = f"{datetime.now().date().year if (datetime.now().date().month+3)<=12 else datetime.now().date().year+1}-{(datetime.now().date().month + 3) if (datetime.now().date().month+3)<=12 else (datetime.now().date().month+3-12)}-{datetime.now().date().day}"
    if request.method == 'POST':
        origin = request.POST.get('Origin')
        destination = request.POST.get('Destination')
        depart_date = request.POST.get('DepartDate')
        seat = request.POST.get('SeatClass')
        trip_type = request.POST.get('TripType')
        if(trip_type == '1'):
            return render(request, 'flight/index.html', {
            'origin': origin,
            'destination': destination,
            'depart_date': depart_date,
            'seat': seat.lower(),
            'trip_type': trip_type
        })
        elif(trip_type == '2'):
            return_date = request.POST.get('ReturnDate')
            return render(request, 'flight/index.html', {
            'min_date': min_date,
            'max_date': max_date,
            'origin': origin,
            'destination': destination,
            'depart_date': depart_date,
            'seat': seat.lower(),
            'trip_type': trip_type,
            'return_date': return_date
        })
    else:
        return render(request, 'flight/index.html', {
            'min_date': min_date,
            'max_date': max_date
        })

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
            
        else:
            return render(request, "flight/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('index'))
        else:
            return render(request, "flight/login.html")

def register_view(request):
    if request.method == "POST":
        fname = request.POST['firstname']
        lname = request.POST['lastname']
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensuring password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "flight/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.first_name = fname
            user.last_name = lname
            user.save()
        except:
            return render(request, "flight/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "flight/register.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def query(request, q):
    places = Place.objects.all()
    filters = []
    q = q.lower()
    for place in places:
        if (q in place.city.lower()) or (q in place.airport.lower()) or (q in place.code.lower()) or (q in place.country.lower()):
            filters.append(place)
    return JsonResponse([{'code':place.code, 'city':place.city, 'country': place.country} for place in filters], safe=False)

@csrf_exempt
def flight(request):
    o_place = request.GET.get('Origin')
    d_place = request.GET.get('Destination')
    trip_type = request.GET.get('TripType')
    departdate = request.GET.get('DepartDate')
    depart_date = datetime.strptime(departdate, "%Y-%m-%d")
    return_date = None

    if trip_type == '2':
        returndate = request.GET.get('ReturnDate')
        return_date = datetime.strptime(returndate, "%Y-%m-%d")
        flightday2 = Week.objects.get(number=return_date.weekday())  ##
        origin2 = Place.objects.get(code=d_place.upper())  ##
        destination2 = Place.objects.get(code=o_place.upper())  ##

    seat = request.GET.get('SeatClass')

    flightday = Week.objects.get(number=depart_date.weekday())
    destination = Place.objects.get(code=d_place.upper())
    origin = Place.objects.get(code=o_place.upper())

    # 初始化 min_duration 和 max_duration
    min_duration = 0
    max_duration = 0

    if seat == 'economy':
        flights = Flight.objects.filter(depart_day=flightday, origin=origin, destination=destination).exclude(economy_fare=0).order_by('economy_fare')
        try:
            max_price = flights.last().economy_fare
            min_price = flights.first().economy_fare
            min_duration = flights.order_by('duration').first().duration
            max_duration = flights.order_by('-duration').first().duration
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':  ##
            flights2 = Flight.objects.filter(depart_day=flightday2, origin=origin2, destination=destination2).exclude(economy_fare=0).order_by('economy_fare')  ##
            try:
                max_price2 = flights2.last().economy_fare  ##
                min_price2 = flights2.first().economy_fare  ##
                min_duration2 = flights2.order_by('duration').first().duration
                max_duration2 = flights2.order_by('-duration').first().duration
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##
                min_duration2 = 0
                max_duration2 = 0

    elif seat == 'business':
        flights = Flight.objects.filter(depart_day=flightday, origin=origin, destination=destination).exclude(business_fare=0).order_by('business_fare')
        try:
            max_price = flights.last().business_fare
            min_price = flights.first().business_fare
            min_duration = flights.order_by('duration').first().duration
            max_duration = flights.order_by('-duration').first().duration
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':  ##
            flights2 = Flight.objects.filter(depart_day=flightday2, origin=origin2, destination=destination2).exclude(business_fare=0).order_by('business_fare')  ##
            try:
                max_price2 = flights2.last().business_fare  ##
                min_price2 = flights2.first().business_fare  ##
                min_duration2 = flights2.order_by('duration').first().duration
                max_duration2 = flights2.order_by('-duration').first().duration
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##
                min_duration2 = 0
                max_duration2 = 0

    elif seat == 'first':
        flights = Flight.objects.filter(depart_day=flightday, origin=origin, destination=destination).exclude(first_fare=0).order_by('first_fare')
        try:
            max_price = flights.last().first_fare
            min_price = flights.first().first_fare
            min_duration = flights.order_by('duration').first().duration
            max_duration = flights.order_by('-duration').first().duration
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':  ##
            flights2 = Flight.objects.filter(depart_day=flightday2, origin=origin2, destination=destination2).exclude(first_fare=0).order_by('first_fare')
            try:
                max_price2 = flights2.last().first_fare  ##
                min_price2 = flights2.first().first_fare  ##
                min_duration2 = flights2.order_by('duration').first().duration
                max_duration2 = flights2.order_by('-duration').first().duration
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##
                min_duration2 = 0
                max_duration2 = 0  ##

    #print(calendar.day_name[depart_date.weekday()])
    if trip_type == '2':
        return render(request, "flight/search.html", {
            'flights': flights,
            'origin': origin,
            'destination': destination,
            'flights2': flights2,  ##
            'origin2': origin2,  ##
            'destination2': destination2,  ##
            'seat': seat.capitalize(),
            'trip_type': trip_type,
            'depart_date': depart_date,
            'return_date': return_date,
            'max_price': math.ceil(max_price/100)*100,
            'min_price': math.floor(min_price/100)*100,
            'max_price2': math.ceil(max_price2/100)*100,  ##
            'min_price2': math.floor(min_price2/100)*100,  ##
            'min_duration': min_duration,
            'max_duration': max_duration,
            'min_duration2': min_duration2,
            'max_duration2': max_duration2,
        })
    else:
        return render(request, "flight/search.html", {
            'flights': flights,
            'origin': origin,
            'destination': destination,
            'seat': seat.capitalize(),
            'trip_type': trip_type,
            'depart_date': depart_date,
            'return_date': return_date,
            'max_price': math.ceil(max_price/100)*100,
            'min_price': math.floor(min_price/100)*100,
            'min_duration': min_duration,
            'max_duration': max_duration,
        })


def review(request):
    flight_1 = request.GET.get('flight1Id')
    date1 = request.GET.get('flight1Date')
    seat = request.GET.get('seatClass')
    round_trip = False
    if request.GET.get('flight2Id'):
        round_trip = True

    if round_trip:
        flight_2 = request.GET.get('flight2Id')
        date2 = request.GET.get('flight2Date')

    if request.user.is_authenticated:
        flight1 = Flight.objects.get(id=flight_1)
        flight1ddate = datetime(int(date1.split('-')[2]),int(date1.split('-')[1]),int(date1.split('-')[0]),flight1.depart_time.hour,flight1.depart_time.minute)
        flight1adate = (flight1ddate + flight1.duration)
        flight2 = None
        flight2ddate = None
        flight2adate = None
        if round_trip:
            flight2 = Flight.objects.get(id=flight_2)
            flight2ddate = datetime(int(date2.split('-')[2]),int(date2.split('-')[1]),int(date2.split('-')[0]),flight2.depart_time.hour,flight2.depart_time.minute)
            flight2adate = (flight2ddate + flight2.duration)
        #print("//////////////////////////////////")
        #print(f"flight1ddate: {flight1adate-flight1ddate}")
        #print("//////////////////////////////////")
        if round_trip:
            return render(request, "flight/book.html", {
                'flight1': flight1,
                'flight2': flight2,
                "flight1ddate": flight1ddate,
                "flight1adate": flight1adate,
                "flight2ddate": flight2ddate,
                "flight2adate": flight2adate,
                "seat": seat,
                "fee": FEE
            })
        return render(request, "flight/book.html", {
            'flight1': flight1,
            "flight1ddate": flight1ddate,
            "flight1adate": flight1adate,
            "seat": seat,
            "fee": FEE
        })
    else:
        return HttpResponseRedirect(reverse("login"))

def book(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            flight_1 = request.POST.get('flight1')
            flight_1date = request.POST.get('flight1Date')
            flight_1class = request.POST.get('flight1Class')
            f2 = False
            if request.POST.get('flight2'):
                flight_2 = request.POST.get('flight2')
                flight_2date = request.POST.get('flight2Date')
                flight_2class = request.POST.get('flight2Class')
                f2 = True
            countrycode = request.POST['countryCode']
            mobile = request.POST['mobile']
            email = request.POST['email']
            flight1 = Flight.objects.get(id=flight_1)
            if f2:
                flight2 = Flight.objects.get(id=flight_2)
            passengerscount = request.POST['passengersCount']
            passengers=[]
            for i in range(1,int(passengerscount)+1):
                fname = request.POST[f'passenger{i}FName']
                lname = request.POST[f'passenger{i}LName']
                gender = request.POST[f'passenger{i}Gender']
                passengers.append(Passenger.objects.create(first_name=fname,last_name=lname,gender=gender.lower()))
            coupon = request.POST.get('coupon')
            
            try:
                ticket1 = createticket(request.user,passengers,passengerscount,flight1,flight_1date,flight_1class,coupon,countrycode,email,mobile)
                if f2:
                    ticket2 = createticket(request.user,passengers,passengerscount,flight2,flight_2date,flight_2class,coupon,countrycode,email,mobile)

                if(flight_1class == 'Economy'):
                    if f2:
                        fare = (flight1.economy_fare*int(passengerscount))+(flight2.economy_fare*int(passengerscount))
                    else:
                        fare = flight1.economy_fare*int(passengerscount)
                elif (flight_1class == 'Business'):
                    if f2:
                        fare = (flight1.business_fare*int(passengerscount))+(flight2.business_fare*int(passengerscount))
                    else:
                        fare = flight1.business_fare*int(passengerscount)
                elif (flight_1class == 'First'):
                    if f2:
                        fare = (flight1.first_fare*int(passengerscount))+(flight2.first_fare*int(passengerscount))
                    else:
                        fare = flight1.first_fare*int(passengerscount)
            except Exception as e:
                return HttpResponse(e)
            

            if f2:    ##
                return render(request, "flight/payment.html", { ##
                    'fare': fare+FEE,   ##
                    'ticket': ticket1.id,   ##
                    'ticket2': ticket2.id   ##
                })  ##
            return render(request, "flight/payment.html", {
                'fare': fare+FEE,
                'ticket': ticket1.id
            })
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return HttpResponse("Method must be post.")

def payment(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            ticket_id = request.POST['ticket']
            t2 = False
            if request.POST.get('ticket2'):
                ticket2_id = request.POST['ticket2']
                t2 = True
            fare = request.POST.get('fare')
            card_number = request.POST['cardNumber']
            card_holder_name = request.POST['cardHolderName']
            exp_month = request.POST['expMonth']
            exp_year = request.POST['expYear']
            cvv = request.POST['cvv']

            try:
                ticket = Ticket.objects.get(id=ticket_id)
                ticket.status = 'CONFIRMED'
                ticket.booking_date = datetime.now()
                ticket.save()
                if t2:
                    ticket2 = Ticket.objects.get(id=ticket2_id)
                    ticket2.status = 'CONFIRMED'
                    ticket2.save()
                    return render(request, 'flight/payment_process.html', {
                        'ticket1': ticket,
                        'ticket2': ticket2
                    })
                return render(request, 'flight/payment_process.html', {
                    'ticket1': ticket,
                    'ticket2': ""
                })
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be post.")
    else:
        return HttpResponseRedirect(reverse('login'))


def ticket_data(request, ref):
    ticket = Ticket.objects.get(ref_no=ref)
    return JsonResponse({
        'ref': ticket.ref_no,
        'from': ticket.flight.origin.code,
        'to': ticket.flight.destination.code,
        'flight_date': ticket.flight_ddate,
        'status': ticket.status
    })

@csrf_exempt
def get_ticket(request):
    ref = request.GET.get("ref")
    ticket1 = Ticket.objects.get(ref_no=ref)
    data = {
        'ticket1':ticket1,
        'current_year': datetime.now().year
    }
    pdf = render_to_pdf('flight/ticket.html', data)
    return HttpResponse(pdf, content_type='application/pdf')


# def bookings(request):
#     if request.user.is_authenticated:
#         tickets = Ticket.objects.filter(user=request.user).order_by('-booking_date')
#         return render(request, 'flight/bookings.html', {
#             'page': 'bookings',
#             'tickets': tickets
#         })
#     else:
#         return HttpResponseRedirect(reverse('login'))

@csrf_exempt
def cancel_ticket(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            ref = request.POST['ref']
            try:
                ticket = Ticket.objects.get(ref_no=ref)
                if ticket.user == request.user:
                    ticket.status = 'CANCELLED'
                    ticket.save()
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({
                        'success': False,
                        'error': "User unauthorised"
                    })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': e
                })
        else:
            return HttpResponse("User unauthorised")
    else:
        return HttpResponse("Method must be POST.")

def resume_booking(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            ref = request.POST['ref']
            ticket = Ticket.objects.get(ref_no=ref)
            if ticket.user == request.user:
                return render(request, "flight/payment.html", {
                    'fare': ticket.total_fare,
                    'ticket': ticket.id
                })
            else:
                return HttpResponse("User unauthorised")
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return HttpResponse("Method must be post.")

def contact(request):
    return render(request, 'flight/contact.html')

def privacy_policy(request):
    return render(request, 'flight/privacy-policy.html')

def terms_and_conditions(request):
    return render(request, 'flight/terms.html')

def about_us(request):
    return render(request, 'flight/about.html')

def geocode_address(request):
    # get adderss from request
    address = request.GET.get('address', '')
    if not address:
        return JsonResponse({"error": "Address is required"}, status=400)

    # use Geocoding API
    api_key = settings.GOOGLE_MAPS_API_KEY
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url)

    # handle result from API 
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return JsonResponse({'lat': location['lat'], 'lng': location['lng']})
        else:
            return JsonResponse({"error": data['status']}, status=400)
    return JsonResponse({"error": "Failed to fetch geocoding data"}, status=500)

# def show_map(request):
#     return render(request, 'flight/map.html')
    # return render(request, 'gmap/map_api/templates/map.html')

# 显示所有发布的贴文
@login_required(login_url='/flight/guest_post/')
def list_posts(request):
    posts = Address.objects.filter(user=request.user)
    return render(request, 'flight/list_posts.html', {'posts': posts})

def guest_post(request):
    # 如果沒有登入的話，顯示尚未登入的提示
    return render(request, 'flight/guest_post.html')

def show_post(request):
    if request.method == "POST":
        form = AddressForm(request.POST, request.FILES)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            form.save()
            return redirect('post')  # 替换为你的成功页面
    else:
        form = AddressForm()

    return render(request, 'flight/post.html', {'form': form})
    # return render(request, 'flight/post.html')

def delete_post(request, post_id):
    post = get_object_or_404(Address, id=post_id, user=request.user)  # 驗證貼文屬於目前使用者
    post.delete()  # 刪除資料
    return redirect('post')  # 刪除後重定向到貼文列表頁

def map_view(request):
    addresses = list(Address.objects.values('content', 'address'))
    addresses_json = json.dumps(addresses, cls=DjangoJSONEncoder)
    return render(request, 'flight/map.html', {'addresses_json': addresses_json})


def pin_view(request):
    address = request.GET.get('address')
    posts = Address.objects.filter(user=request.user, address=address)
    return render(request, 'flight/pin_post.html', {'posts': posts})

from googleapiclient.discovery import build
from django.http import JsonResponse
from django.shortcuts import render
from .models import Messages

# 翻譯文本
def translate_text(text, target_language):
    api_key = "AIzaSyDFrVuXNtiGp6PL8wBt_iwEmIjcJNhB4qU"  # Google Translate API 密鑰
    service = build('translate', 'v2', developerKey=api_key)
    result = service.translations().list(q=text, target=target_language).execute()
    return result['translations'][0]['translatedText']

# 顯示聊天視圖
def show_chat(request):
    return render(request, 'flight/chat.html')

# 獲取訊息
def get_messages(request):
    target_language = request.GET.get('lang', 'en')  # 預設語言為英語
    
    if request.user.is_authenticated:
        # 如果用戶已登入，從數據庫讀取訊息
        messages = Messages.objects.all().order_by('timestamp')
        message_data = []
        for msg in messages:
            translated_content = translate_text(msg.content, target_language) if msg.user != request.user else None
            message_data.append({
                'user': msg.user.username,
                'content': msg.content,
                'translated': translated_content,
            })
    else:
        # 如果用戶未登入，從 session 讀取訊息
        messages = request.session.get('chat_messages', [])
        message_data = [{'user': msg['user'], 'content': msg['content'], 'translated': None} for msg in messages]

    return JsonResponse({'messages': message_data})

# 發送訊息
def post_message(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            if request.user.is_authenticated:
                # 如果用戶已登入，存儲到數據庫
                Messages.objects.create(user=request.user, content=content)
            else:
                # 如果用戶未登入，存儲到 session
                new_message = {'user': 'Guest', 'content': content}
                messages = request.session.get('chat_messages', [])
                messages.append(new_message)
                request.session['chat_messages'] = messages
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
