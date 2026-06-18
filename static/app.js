const POLL_INTERVAL_MS = 30_000;
const HOURS = 24;

const UTC_FORMAT = {
  timeZone: "UTC",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

const UTC_TIMESTAMP_FORMAT = {
  timeZone: "UTC",
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

function formatHourLabel(isoString) {
  const date = new Date(isoString);
  return `${date.toLocaleString("en-GB", UTC_FORMAT)} UTC`;
}

function formatTimestamp(isoString) {
  const date = new Date(isoString);
  return `${date.toLocaleString("en-GB", UTC_TIMESTAMP_FORMAT)} UTC`;
}

function formatHourlyWindow(buckets) {
  if (buckets.length === 0) {
    return `Last ${HOURS} hours (UTC)`;
  }

  const start = formatHourLabel(buckets[0].hour).replace(" UTC", "");
  const endHour = new Date(buckets[buckets.length - 1].hour);
  endHour.setUTCHours(endHour.getUTCHours() + 1);
  const end = formatHourLabel(endHour.toISOString()).replace(" UTC", "");
  return `${start} – ${end} UTC`;
}

function sumHourlyByCustomer(buckets) {
  const totals = new Map();

  for (const bucket of buckets) {
    for (const customer of bucket.customers) {
      totals.set(
        customer.customer_id,
        (totals.get(customer.customer_id) || 0) + customer.visits
      );
    }
  }

  return totals;
}

function sumHourlyVisits(buckets) {
  return buckets.reduce((total, bucket) => total + bucket.visits, 0);
}

function createCell(text, className) {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) {
    cell.classList.add(className);
  }
  return cell;
}

function buildHourlyRows(buckets) {
  const rows = [];

  for (const bucket of buckets) {
    const hourLabel = formatHourLabel(bucket.hour);

    if (bucket.customers.length === 0) {
      const row = document.createElement("tr");
      row.classList.add("zero-visits");
      row.append(createCell(hourLabel), createCell("—"), createCell("0", "numeric"));
      rows.push(row);
      continue;
    }

    for (const customer of bucket.customers) {
      const row = document.createElement("tr");
      row.append(
        createCell(hourLabel),
        createCell(customer.customer_id),
        createCell(String(customer.visits), "numeric")
      );
      rows.push(row);
    }
  }

  return rows;
}

function buildCustomerRows(customers, hourlyByCustomer) {
  if (customers.length === 0) {
    const row = document.createElement("tr");
    row.classList.add("empty-state");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "No customers yet";
    row.append(cell);
    return [row];
  }

  return customers.map((customer) => {
    const row = document.createElement("tr");
    const visitsLast24h = hourlyByCustomer.get(customer.customer_id) || 0;
    const progress = `${customer.visits_toward_next_tree} / ${customer.visits_per_tree}`;
    row.append(
      createCell(customer.customer_id),
      createCell(String(visitsLast24h), "numeric"),
      createCell(String(customer.total_visits), "numeric"),
      createCell(progress, "numeric"),
      createCell(String(customer.trees_planted), "numeric")
    );
    return row;
  });
}

function buildTreeEventRows(events) {
  if (events.length === 0) {
    const row = document.createElement("tr");
    row.classList.add("empty-state");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = "No trees planted yet";
    row.append(cell);
    return [row];
  }

  return [...events].reverse().map((event) => {
    const row = document.createElement("tr");
    row.append(
      createCell(formatTimestamp(event.planted_at)),
      createCell(event.customer_id),
      createCell(String(event.visits_per_tree), "numeric")
    );
    return row;
  });
}

function updateHourlyTable(buckets) {
  const tbody = document.getElementById("visits-table-body");
  tbody.replaceChildren(...buildHourlyRows(buckets));
  document.getElementById("hourly-total-visits").textContent = String(sumHourlyVisits(buckets));
  document.getElementById("hourly-window").textContent = formatHourlyWindow(buckets);
}

function updateCustomersTable(customers, hourlyByCustomer) {
  const tbody = document.getElementById("customers-table-body");
  tbody.replaceChildren(...buildCustomerRows(customers, hourlyByCustomer));
}

function updateTreeEventsTable(events) {
  const tbody = document.getElementById("tree-events-table-body");
  tbody.replaceChildren(...buildTreeEventRows(events));
}

async function loadConfig() {
  const response = await fetch("/api/config");
  const data = await response.json();
  document.getElementById("visits-per-tree").textContent = data.default_visits_per_tree;
}

async function loadHourlyStats() {
  const response = await fetch(`/api/stats/hourly?hours=${HOURS}`);
  const data = await response.json();
  return data.buckets;
}

async function loadCustomers() {
  const response = await fetch("/api/customers");
  const data = await response.json();
  return data.customers;
}

async function loadTreeEvents() {
  const response = await fetch("/api/trees/events");
  const data = await response.json();
  return data.events;
}

async function refresh() {
  try {
    const [_, buckets, customers, events] = await Promise.all([
      loadConfig(),
      loadHourlyStats(),
      loadCustomers(),
      loadTreeEvents(),
    ]);
    const hourlyByCustomer = sumHourlyByCustomer(buckets);

    updateHourlyTable(buckets);
    updateCustomersTable(customers, hourlyByCustomer);
    updateTreeEventsTable(events);
    document.getElementById("last-updated").textContent = new Date().toLocaleString();
  } catch (error) {
    console.error("Failed to refresh dashboard:", error);
  }
}

document.getElementById("hourly-hours-label").textContent = String(HOURS);

refresh();
setInterval(refresh, POLL_INTERVAL_MS);
