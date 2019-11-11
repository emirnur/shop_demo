from datetime import datetime

from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from webapp.models import Product, Order, OrderProduct


class VisitMixin:

    def visit(self, request):
        visits = request.session.get('visits', [])
        old_page = request.session.get('old_page')
        old_time = request.session.get('old_time')
        if old_page:
            count = 0
            for i in visits:
                i[0] = old_page
                now = datetime.now()
                diff = now - old_time.strptime('%Y-%m-%d %H:%M:%S')
                old_time = now.strftime('%Y-%m-%d %H:%M:%S')
                count += 1
                i[1] = diff.seconds
                i[2] = count
            request.session['visits'] = visits
            request.session['old_page'] = old_page
            request.session['old_time'] = old_time
        else:
            visits = [[]]
            visits[0][0] = request.session['old_page']
            visits[0][1] = request.session['old_time']
            visits[0][2] = 1
            request.session['visits'] = visits


class IndexView(VisitMixin, ListView):
    model = Product
    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        super().visit(request)
        return super().get(request, *args, **kwargs)


class ProductView(VisitMixin, DetailView):
    model = Product
    template_name = 'product/detail.html'

    def get(self, request, *args, **kwargs):
        super().visit(request)
        return super().get(request, *args, **kwargs)


class ProductCreateView(VisitMixin, CreateView):
    model = Product
    template_name = 'product/create.html'
    fields = ('name', 'category', 'price', 'photo')
    success_url = reverse_lazy('webapp:index')

    def get(self, request, *args, **kwargs):
        super().visit(request)
        return super().get(request, *args, **kwargs)


class BasketChangeView(View):
    def get(self, request, *args, **kwargs):
        products = request.session.get('products', [])

        pk = request.GET.get('pk')
        action = request.GET.get('action')
        next_url = request.GET.get('next', reverse('webapp:index'))

        if action == 'add':
            products.append(pk)
        else:
            for product_pk in products:
                if product_pk == pk:
                    products.remove(product_pk)
                    break

        request.session['products'] = products
        request.session['products_count'] = len(products)

        return redirect(next_url)


# class BasketView(TemplateView):
#     template_name = 'product/basket.html'
#
#     def get_context_data(self, **kwargs):
#         products = self.request.session.get('products', [])
#
#         totals = {}
#         for product_pk in products:
#             if product_pk not in totals:
#                 totals[product_pk] = 0
#             totals[product_pk] += 1
#
#         basket = []
#         basket_total = 0
#         for pk, qty in totals.items():
#             product = Product.objects.get(pk=int(pk))
#             total = product.price * qty
#             basket_total += total
#             basket.append({'product': product, 'qty': qty, 'total': total})
#
#         kwargs['basket'] = basket
#         kwargs['basket_total'] = basket_total
#
#         return super().get_context_data(**kwargs)


class BasketView(VisitMixin, CreateView):
    model = Order
    fields = ('first_name', 'last_name', 'phone', 'email')
    template_name = 'product/basket.html'
    success_url = reverse_lazy('webapp:index')

    def get(self, request, *args, **kwargs):
        super().visit(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        basket, basket_total = self._prepare_basket()
        kwargs['basket'] = basket
        kwargs['basket_total'] = basket_total
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        if self._basket_empty():
            form.add_error(None, 'В корзине отсутствуют товары!')
            return self.form_invalid(form)
        response = super().form_valid(form)
        self._save_order_products()
        self._clean_basket()
        return response

    def _prepare_basket(self):
        totals = self._get_totals()
        basket = []
        basket_total = 0
        for pk, qty in totals.items():
            product = Product.objects.get(pk=int(pk))
            total = product.price * qty
            basket_total += total
            basket.append({'product': product, 'qty': qty, 'total': total})
        return basket, basket_total

    def _get_totals(self):
        products = self.request.session.get('products', [])
        totals = {}
        for product_pk in products:
            if product_pk not in totals:
                totals[product_pk] = 0
            totals[product_pk] += 1
        return totals

    def _basket_empty(self):
        products = self.request.session.get('products', [])
        return len(products) == 0

    def _save_order_products(self):
        totals = self._get_totals()
        for pk, qty in totals.items():
            OrderProduct.objects.create(product_id=pk, order=self.object, amount=qty)

    def _clean_basket(self):
        if 'products' in self.request.session:
            self.request.session.pop('products')
        if 'products_count' in self.request.session:
            self.request.session.pop('products_count')